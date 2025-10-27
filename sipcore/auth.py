# sipcore/auth.py
import hashlib, re, time, os
from .message import SIPMessage
from .utils import gen_tag

_REALM = "sip.local"  # 你可以放到 config 后续再抽
_NONCES = {}

def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def _parse_authorization(h: str) -> dict:
    # 解析形如：Digest username="1001", realm="sip.local", nonce="...", uri="sip:sip.local", response="..."
    out = {}
    m_auth = re.match(r'^\s*Digest\s+(.*)$', h, re.I)
    if not m_auth:
        return out
    parts = re.findall(r'(\w+)=(".*?"|[^,]+)', m_auth.group(1))
    for k, v in parts:
        out[k.lower()] = v.strip('"')
    return out

def make_401(req: SIPMessage) -> SIPMessage:
    nonce = os.urandom(8).hex() + str(int(time.time()))
    _NONCES[nonce] = time.time()
    r = SIPMessage(start_line="SIP/2.0 401 Unauthorized")
    for v in req.headers.get("via", []):
        r.add_header("via", v)
    to_val = req.get("to") or ""
    if "tag=" not in to_val:
        to_val = f"{to_val};tag={gen_tag()}"
    r.add_header("to", to_val)
    r.add_header("from", req.get("from") or "")
    r.add_header("call-id", req.get("call-id") or "")
    r.add_header("cseq", req.get("cseq") or "")
    r.add_header("www-authenticate",
        f'Digest realm="{_REALM}", nonce="{nonce}", algorithm=MD5, qop="auth"')
    r.add_header("content-length", "0")
    return r

def check_digest(req: SIPMessage, users: dict[str, str]) -> bool:
    auth = req.get("authorization")
    if not auth:
        return False
    a = _parse_authorization(auth)
    username = a.get("username")
    realm = a.get("realm")
    nonce = a.get("nonce")
    uri = a.get("uri")
    response = a.get("response")
    cnonce = a.get("cnonce", "")
    nc = a.get("nc", "")
    qop = a.get("qop", "")

    if not (username and realm and nonce and uri and response):
        return False
    if realm != _REALM:
        return False
    if nonce not in _NONCES:   # 简单防重放（演示用）
        return False
    password = users.get(username)
    if not password:
        return False

    method = req.start_line.split()[0]
    ha1 = _md5(f"{username}:{realm}:{password}")
    ha2 = _md5(f"{method}:{uri}")
    if qop:  # auth
        expect = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    else:
        expect = _md5(f"{ha1}:{nonce}:{ha2}")
    return expect.lower() == response.lower()
