# run.py
import asyncio, time, re, socket
from sipcore.transport_udp import UDPServer
from sipcore.parser import parse
from sipcore.message import SIPMessage
from sipcore.utils import gen_tag, sip_date
from sipcore.auth import make_401, check_digest
from sipcore.logger import init_logging
from sipcore.timers import create_timers
from sipcore.cdr import init_cdr, get_cdr
from sipcore.user_manager import init_user_manager, get_user_manager
from sipcore.sdp_parser import extract_sdp_info

# 初始化日志系统
log = init_logging(level="DEBUG", log_file="logs/ims-sip-server.log")

# 初始化配置管理器
from config.config_manager import init_config_manager
config_mgr = init_config_manager("config/config.json")

# 初始化 CDR 系统（日志输出已移到 init_cdr 内部）
cdr = init_cdr(base_dir="CDR")

# 初始化用户管理系统（日志输出已移到 init_user_manager 内部）
user_mgr = init_user_manager(data_file="data/users.json")

# ====== 配置区 ======
SERVER_IP = "192.168.8.126"
SERVER_PORT = 5060
SERVER_URI = f"sip:{SERVER_IP}:{SERVER_PORT};lr"   # 用于Record-Route
ALLOW = "INVITE, ACK, CANCEL, BYE, OPTIONS, PRACK, UPDATE, REFER, NOTIFY, SUBSCRIBE, MESSAGE, REGISTER"

# 网络环境配置
# LOCAL_NETWORKS: 本机或局域网内的网络地址列表，这些地址不需要转换
# 如果是真实部署，服务器IP应该是局域网地址（如 192.168.1.100）
LOCAL_NETWORKS = [
    "127.0.0.1",          # 本机
    "localhost",          # 本机别名
    SERVER_IP,            # 服务器地址
]
# 如果需要支持局域网，可以添加：
LOCAL_NETWORKS.extend(["192.168.8.0/16"])

# FORCE_LOCAL_ADDR: 强制使用本地地址（仅用于单机测试）
# 设置为 False 时，支持真实的多机网络环境
FORCE_LOCAL_ADDR = False   # True: 本机测试模式 | False: 真实网络模式

# 注册绑定: AOR -> list of bindings: [{"contact": "sip:1001@ip:port", "expires": epoch}]
REG_BINDINGS: dict[str, list[dict]] = {}

# 请求追踪：Call-ID -> 原始发送地址
PENDING_REQUESTS: dict[str, tuple[str, int]] = {}

# 对话追踪：Call-ID -> (主叫地址, 被叫地址)
DIALOGS: dict[str, tuple[tuple[str, int], tuple[str, int]]] = {}

# 事务追踪：Call-ID -> 服务器添加的 Via branch（用于 CANCEL 匹配）
# INVITE 事务的 branch 需要被 CANCEL 复用，以满足某些非标准客户端（如 Zoiper 2.x）的要求
INVITE_BRANCHES: dict[str, str] = {}

# ====== 工具函数 ======
def _aor_from_from(from_val: str | None) -> str:
    if not from_val:
        return ""
    s = from_val
    if "<sip:" in s and ">" in s:
        uri = s[s.find("<")+1:s.find(">")]
    else:
        p = s.find("sip:")
        uri = s[p:] if p >= 0 else s
    semi = uri.find(";")
    if semi > 0:
        uri = uri[:semi]
    return uri  # e.g., sip:1002@sip.local

def _same_user(uri1: str, uri2: str) -> bool:
    """比较两个 SIP URI 是否同一用户（忽略域名和端口）"""
    import re
    def extract_user(u):
        m = re.search(r"sip:([^@;>]+)", u)
        return m.group(1) if m else u
    return extract_user(uri1) == extract_user(uri2)

def _aor_from_to(to_val: str | None) -> str:
    if not to_val:
        return ""
    s = to_val
    if "<sip:" in s and ">" in s:
        uri = s[s.find("<")+1:s.find(">")]
    else:
        p = s.find("sip:")
        uri = s[p:] if p >= 0 else s
    semi = uri.find(";")
    if semi > 0:
        uri = uri[:semi]
    return uri  # e.g., sip:1001@sip.local

def _parse_contacts(req: SIPMessage):
    out = []
    for c in req.headers.get("contact", []):
        uri = c
        if "<" in c and ">" in c:
            uri = c[c.find("<")+1:c.find(">")]
        exp = 3600
        m = re.search(r"expires=(\d+)", c, re.I)
        if m:
            exp = int(m.group(1))
        else:
            e = req.get("expires")
            if e and e.isdigit():
                exp = int(e)
        out.append({"contact": uri, "expires": exp})
    return out

def _host_port_from_via(via_val: str) -> tuple[str, int]:
    # 例：Via: SIP/2.0/UDP 192.168.1.50:5062;branch=z9hG4bK;rport=5060;received=192.168.1.50
    # 优先使用 received 和 rport 参数（RFC 3261 Section 18.2.2）
    
    # 先检查 received 参数
    received_match = re.search(r"received=([^\s;]+)", via_val, re.I)
    if received_match:
        host = received_match.group(1).strip()
        
        # 检查 rport 参数
        rport_match = re.search(r"rport=(\d+)", via_val, re.I)
        if rport_match:
            port = int(rport_match.group(1))
            return (host, port)
        else:
            # 没有 rport，使用 sent-by 的端口
            sent_by_match = re.search(r"SIP/2\.0/\w+\s+([^;]+)", via_val, re.I)
            if sent_by_match:
                sent_by = sent_by_match.group(1).strip()
                if ":" in sent_by:
                    _, p = sent_by.rsplit(":", 1)
                    try:
                        return (host, int(p))
                    except:
                        return (host, 5060)
            return (host, 5060)
    
    # 没有 received 参数，使用 sent-by
    m = re.search(r"SIP/2\.0/\w+\s+([^;]+)", via_val, re.I)
    if not m:
        return ("", 0)
    sent_by = m.group(1).strip()
    if ":" in sent_by:
        h, p = sent_by.rsplit(":", 1)
        try:
            return (h, int(p))
        except:
            return (h, 5060)
    else:
        return (sent_by, 5060)

def _host_port_from_sip_uri(uri: str) -> tuple[str, int]:
    # 例：sip:1002@192.168.1.60:5066;transport=udp
    # 或 sip:192.168.1.60:5066
    u = uri
    if u.startswith("sip:"):
        u = u[4:]
    # 去掉用户@部分
    if "@" in u:
        u = u.split("@", 1)[1]
    # 去掉参数
    if ";" in u:
        u = u.split(";", 1)[0]
    if ":" in u:
        host, port = u.rsplit(":", 1)
        try:
            return host, int(port)
        except:
            return host, 5060
    return u, 5060

def _ensure_header(msg: SIPMessage, name: str, default: str):
    if not msg.get(name):
        msg.add_header(name, default)

def _decrement_max_forwards(msg: SIPMessage) -> bool:
    mf = msg.get("max-forwards")
    try:
        v = int(mf) if mf is not None else 70
    except:
        v = 70
    v -= 1
    if v < 0:
        return False
    # 覆盖：删除旧的，再加新的
    msg.headers.pop("max-forwards", None)
    msg.add_header("max-forwards", str(v))
    return True

def _add_top_via(msg: SIPMessage, branch: str):
    via = f"SIP/2.0/UDP {SERVER_IP}:{SERVER_PORT};branch={branch};rport"
    # 插入为第一条 Via
    old = msg.headers.get("via", [])
    msg.headers["via"] = [via] + old

def _pop_top_via(resp: SIPMessage):
    vias = resp.headers.get("via", [])
    if vias:
        vias.pop(0)
    if vias:
        resp.headers["via"] = vias
    else:
        resp.headers.pop("via", None)

def _is_request(start_line: str) -> bool:
    return not start_line.startswith("SIP/2.0")

def _method_of(msg: SIPMessage) -> str:
    return msg.start_line.split()[0]

def _is_initial_request(msg: SIPMessage) -> bool:
    # 初始请求：无 "Route" 指向我们，且是新的对话（简单判断：无 "To" tag）
    to = msg.get("to") or ""
    has_tag = "tag=" in to
    routes = msg.headers.get("route", [])
    targeted_us = any(SERVER_IP in r or str(SERVER_PORT) in r for r in routes)
    return (not has_tag) or targeted_us  # 宽松判断即可

def _strip_our_top_route_and_get_next(msg: SIPMessage) -> None:
    routes = msg.headers.get("route", [])
    if not routes:
        return
    top = routes[0]
    if SERVER_IP in top or str(SERVER_PORT) in top:
        routes.pop(0)
        if routes:
            msg.headers["route"] = routes
        else:
            msg.headers.pop("route", None)

def _add_record_route_for_initial(msg: SIPMessage):
    # 在初始请求上插入 RR
    msg.add_header("record-route", f"<{SERVER_URI}>")

def _make_response(req: SIPMessage, code: int, reason: str, extra_headers: dict | None = None, body: bytes = b"") -> SIPMessage:
    r = SIPMessage(start_line=f"SIP/2.0 {code} {reason}")
    for v in req.headers.get("via", []):
        r.add_header("via", v)
    to_val = req.get("to") or ""
    if "tag=" not in to_val and code >= 200:
        to_val = f"{to_val};tag={gen_tag()}"
    r.add_header("to", to_val)
    r.add_header("from", req.get("from") or "")
    r.add_header("call-id", req.get("call-id") or "")
    r.add_header("cseq", req.get("cseq") or "")
    r.add_header("server", "ims-sip-server/0.0.3")
    r.add_header("allow", ALLOW)
    r.add_header("date", sip_date())
    r.add_header("content-length", "0" if not body else str(len(body)))
    if extra_headers:
        for k, v in extra_headers.items():
            r.add_header(k, v)
    return r

# ====== 业务处理 ======

def handle_register(msg: SIPMessage, addr, transport):
    # 从 user_manager 获取 ACTIVE 用户构建认证字典
    try:
        active_users = {
            user['username']: user['password'] 
            for user in user_mgr.get_all_users() 
            if user.get('status') == 'ACTIVE'
        }
    except Exception as e:
        log.error(f"Failed to get users from user_manager: {e}")
        active_users = {}
    
    # 检查认证
    if not check_digest(msg, active_users):
        resp = make_401(msg)
        transport.sendto(resp.to_bytes(), addr)
        log.tx(addr, resp.start_line, extra="Auth failed")
        # CDR: 401 是正常的 SIP 认证挑战流程，不记录为失败
        # 只有当客户端多次尝试后仍失败，或返回其他错误码时才记录失败
        return

    aor = _aor_from_to(msg.get("to"))
    if not aor:
        resp = _make_response(msg, 400, "Bad Request")
        transport.sendto(resp.to_bytes(), addr)
        log.tx(addr, resp.start_line)
        return

    binds = _parse_contacts(msg)

    # --- 自动修正 Contact 的 IP/端口 ---
    fixed_binds = []
    for b in binds:
        contact = b["contact"]
        # 提取 sip:user@IP:port
        import re
        contact = re.sub(r"@[^;>]+", f"@{addr[0]}:{addr[1]}", contact)
        b["contact"] = contact
        fixed_binds.append(b)
    binds = fixed_binds
    # ------------------------------------

    now = int(time.time())
    lst = REG_BINDINGS.setdefault(aor, [])
    lst[:] = [b for b in lst if b["expires"] > now]
    for b in binds:
        if b["expires"] == 0:
            lst[:] = [x for x in lst if x["contact"] != b["contact"]]
        else:
            abs_exp = now + b["expires"]
            for x in lst:
                if x["contact"] == b["contact"]:
                    x["expires"] = abs_exp
                    break
            else:
                lst.append({"contact": b["contact"], "expires": abs_exp})

    resp = _make_response(msg, 200, "OK")
    for b in lst:
        resp.add_header("contact", f"<{b['contact']}>")
    transport.sendto(resp.to_bytes(), addr)
    log.tx(addr, resp.start_line, extra=f"bindings={len(lst)}")
    
    # CDR: 记录注册/注销事件
    if binds and binds[0]["expires"] == 0:
        # 注销
        cdr.record_unregister(
            caller_uri=aor,
            caller_addr=addr,
            contact=binds[0]["contact"],
            call_id=msg.get("call-id") or "",
            user_agent=msg.get("user-agent") or "",
            cseq=msg.get("cseq") or ""
        )
    else:
        # 注册成功
        contact = lst[0]["contact"] if lst else ""
        expires = binds[0]["expires"] if binds else 3600
        cdr.record_register(
            caller_uri=aor,
            caller_addr=addr,
            contact=contact,
            expires=expires,
            success=True,
            status_code=200,
            status_text="OK",
            call_id=msg.get("call-id") or "",
            user_agent=msg.get("user-agent") or "",
            cseq=msg.get("cseq") or "",
            server_ip=SERVER_IP,
            server_port=SERVER_PORT
        )

def _forward_request(msg: SIPMessage, addr, transport):
    """
    将请求转发到下一跳：
    - 初始 INVITE：根据 REG_BINDINGS 选择被叫 Contact，改写 R-URI，插入 Record-Route
    - in-dialog（带 Route 指向我们）：弹出顶层 Route
    - 统一：加顶层 Via、递减 Max-Forwards
    """
    method = _method_of(msg)

    # 忽略/丢弃 Max-Forwards<=0
    if not _decrement_max_forwards(msg):
        resp = _make_response(msg, 483, "Too Many Hops")
        transport.sendto(resp.to_bytes(), addr)
        log.tx(addr, resp.start_line)
        return

    # 在删除 Route 之前，先保存 Route 信息（用于 ACK 类型判断）
    call_id = msg.get("call-id")
    original_routes = msg.headers.get("route", [])
    has_route_before_strip = len(original_routes) > 0

    # in-dialog：如果顶层 Route 就是我们，弹掉它
    _strip_our_top_route_and_get_next(msg)

    # 防止重复请求：检查 Call-ID 是否已经在 DIALOGS 中（可能是重发）
    call_id = msg.get("call-id")
    if call_id and call_id in DIALOGS:
        # 这是一个已知对话的请求（可能是重发的 INVITE）
        # 对于重发的 INVITE in-dialog 请求，发送 100 Trying 响应，避免客户端重复重试
        if method == "INVITE":
            log.debug(f"[REQ-TRACK] Call-ID {call_id} is in DIALOGS, responding 100 Trying to duplicate INVITE")
            resp = _make_response(msg, 100, "Trying")
            transport.sendto(resp.to_bytes(), addr)
            log.tx(addr, resp.start_line, extra="duplicate INVITE handling")
            return
        # 其他 in-dialog 请求（BYE, UPDATE等）继续处理
        log.debug(f"[REQ-TRACK] Call-ID {call_id} is in DIALOGS, treating as in-dialog {method} request")

    # CANCEL/ACK/BYE/UPDATE 请求特殊处理：修正 R-URI（去除外部 IP 和 ;ob 参数，使用本地地址）
    # RFC 3261 重要规则：
    # - CANCEL：R-URI 必须和对应的 INVITE 转发后的 R-URI 一致
    # - 非 2xx 响应的 ACK：R-URI 必须与原始 INVITE 相同，不能修改！
    # - 2xx 响应的 ACK：R-URI 应该使用 Contact 头中的地址，可以修改
    # - BYE/UPDATE：对话内请求，可以修改
    if method == "CANCEL":
        # CANCEL R-URI 修正逻辑
        # RFC 3261: CANCEL 的 R-URI 必须和对应的 INVITE 一致
        # 由于服务器转发 INVITE 时已经修改了 R-URI，CANCEL 也必须使用相同的修正后的 R-URI
        try:
            ruri = msg.start_line.split()[1]
            # 如果 R-URI 指向服务器地址，需要修正为实际被叫地址
            if f"{SERVER_IP}" in ruri or "127.0.0.1" in ruri or "@192.168.137.1" in ruri:
                # 提取被叫 AOR（从 To 头）
                aor = _aor_from_to(msg.get("to"))
                if not aor:
                    # 如果 To 头没有 AOR，从 R-URI 提取
                    aor = _aor_from_to(ruri)
                
                targets = REG_BINDINGS.get(aor, [])
                now = int(time.time())
                targets = [t for t in targets if t["expires"] > now]
                if targets:
                    target_uri = targets[0]["contact"]
                    # 完全移除所有参数（包括 ;ob, transport 等）
                    import re
                    target_uri = re.sub(r";[^,]*", "", target_uri)  # 移除所有 ; 开始的参数
                    target_uri = target_uri.strip()
                    # 改写 R-URI
                    parts = msg.start_line.split()
                    original_ruri = parts[1]
                    parts[1] = target_uri
                    msg.start_line = " ".join(parts)
                    log.debug(f"CANCEL R-URI corrected: {original_ruri} -> {target_uri}")
        except Exception as e:
            log.warning(f"CANCEL R-URI correction failed: {e}")
    elif method in ("BYE", "UPDATE"):
        # BYE 和 UPDATE：对话内请求，可以修正 R-URI
        try:
            ruri = msg.start_line.split()[1]
            # 如果 R-URI 包含外部 IP 或 ;ob 参数，需要修正
            if ";ob" in ruri or "@100." in ruri or "@192." in ruri or "@172." in ruri:
                # 从 To 头获取被叫 AOR
                to_val = msg.get("to")
                to_aor = _aor_from_to(to_val)
                if to_aor:
                    # 查找该 AOR 的本地 contact
                    targets = REG_BINDINGS.get(to_aor, [])
                    if targets:
                        target_uri = targets[0]["contact"]
                        # 完全移除所有参数（包括 ;ob, transport 等）
                        import re
                        # 先清理 URI，提取基本地址
                        target_uri = re.sub(r";[^,]*", "", target_uri)  # 移除所有 ; 开始的参数
                        target_uri = target_uri.strip()
                        # 改写 R-URI
                        parts = msg.start_line.split()
                        parts[1] = target_uri
                        msg.start_line = " ".join(parts)
                        # 清理 Route 和 Record-Route 头，避免 ;ob 和参数问题
                        msg.headers.pop("route", None)
                        msg.headers.pop("record-route", None)
                        log.debug(f"{method} R-URI corrected: {ruri} -> {target_uri}")
        except Exception as e:
            log.warning(f"{method} R-URI correction failed: {e}")
    # ACK 类型判断（用于后续处理）
    is_2xx_ack = False
    if method == "ACK":
        # ACK 特殊处理：区分 2xx 和非 2xx 响应
        # RFC 3261: 
        # - 2xx ACK：通过 Route 头路由（保留 Route）
        # - 非 2xx ACK：透传，保持所有头域不变（包括 R-URI）
        
        # 判断方法：
        # 1. 检查原始 Route 头（删除服务器 Route 之前）：2xx ACK 有 Route
        # 2. 检查 To tag：2xx ACK 必须有 To tag
        # 3. 检查 DIALOGS：Call-ID 在 DIALOGS 说明是已建立的对话
        to_tag = "tag=" in (msg.get("to") or "")
        
        # 使用原始 Route 信息（删除服务器 Route 之前的状态）
        # 2xx ACK：有原始 Route 头或 Call-ID 在 DIALOGS
        if (has_route_before_strip and to_tag) or (to_tag and call_id and call_id in DIALOGS):
            # 2xx ACK：使用 Route 头路由
            is_2xx_ack = True
            log.debug(f"ACK (2xx): Original Route={has_route_before_strip}, To tag=YES, Dialog={call_id in DIALOGS if call_id else False}")
            # ACK 成功转发后，可以清理 DIALOGS（会话已确认建立）
            if call_id and call_id in DIALOGS:
                log.debug(f"[ACK-RECEIVED] ACK for Call-ID {call_id}, dialog confirmed")
        else:
            # 非 2xx ACK：透传，不修改任何头域
            is_2xx_ack = False
            log.debug(f"ACK (non-2xx): Original Route={has_route_before_strip}, To tag={to_tag}")

    # 初始 INVITE/MESSAGE/其他初始请求：查位置，改 R-URI
    if method in ("INVITE", "MESSAGE") and _is_initial_request(msg):
        # --- IMS 模式: 删除 UA 自带的 Route，清理 ;ob 参数 ---
        route_count = len(msg.headers.get("route", []))
        if route_count > 0:
            log.debug(f"[{method}-INITIAL] Deleting {route_count} Route headers")
        msg.headers.pop("route", None)

        # 解析被叫 AOR
        aor = _aor_from_to(msg.get("to")) or msg.start_line.split()[1]
        log.debug(f"[{method}-INITIAL] AOR: {aor} | To: {msg.get('to')}")
        targets = REG_BINDINGS.get(aor, [])
        now = int(time.time())
        targets = [t for t in targets if t["expires"] > now]
        log.debug(f"[{method}-INITIAL] Found {len(targets)} valid bindings for AOR: {aor}")
        if not targets:
            log.warning(f"[{method}-INITIAL] No valid bindings for AOR: {aor}")
            resp = _make_response(msg, 480, "Temporarily Unavailable")
            transport.sendto(resp.to_bytes(), addr)
            log.tx(addr, resp.start_line, extra=f"aor={aor}")
            return

        # 取第一个绑定的 contact，去掉 ;ob / ;transport 等参数
        import re
        target_uri = targets[0]["contact"]
        target_uri = re.sub(r";ob\b", "", target_uri)
        target_uri = re.sub(r";transport=\w+", "", target_uri)

        # 改写 Request-URI
        parts = msg.start_line.split()
        parts[1] = target_uri
        msg.start_line = " ".join(parts)
        # --- 修正 From / To 防环路 ---
        try:
            from_aor = _aor_from_from(msg.get("from"))
            to_aor = _aor_from_to(msg.get("to"))

            # 如果主叫和被叫用户名相同（同一UA呼自己）
            if _same_user(from_aor, to_aor):
                # 强制改写被叫为目标AOR（即被叫注册的Contact）
                targets = REG_BINDINGS.get(to_aor, [])
                if targets:
                    target_uri = targets[0]["contact"]
                    # 改写Request-URI
                    parts = msg.start_line.split()
                    parts[1] = target_uri
                    msg.start_line = " ".join(parts)
                    # 修正From为主叫AOR
                    for aor, binds in REG_BINDINGS.items():
                        for b in binds:
                            ip, port = _host_port_from_sip_uri(b["contact"])
                            if addr[1] == port:
                                msg.headers["from"] = [f"<{aor}>;tag={gen_tag()}"]
                                break
        except Exception as e:
            log.warning(f"From/To normalize failed: {e}")

        # 插入 Record-Route（RFC 3261 强制要求）
        # 当代理修改 R-URI 时，必须添加 Record-Route，
        # 这样后续的 in-dialog 请求（如 ACK, BYE）会通过 Route 头路由回代理
        _add_record_route_for_initial(msg)
        log.debug(f"[RECORD-ROUTE] Added Record-Route for initial INVITE")

    # 顶层 Via（我们）
    # RFC 3261: 
    # - INVITE: 有状态代理，添加服务器 Via，并保存 branch（用于 CANCEL 复用）
    # - CANCEL: 有状态代理，复用对应 INVITE 的 branch（兼容非标准客户端如 Zoiper 2.x）
    # - ACK (非2xx): 无状态转发，不添加 Via，保持与原始 INVITE 的 Via branch 一致
    # - 其他请求: 有状态代理，添加服务器 Via
    # 
    # RFC 3261 Section 9.1 关于 CANCEL:
    # "The CANCEL request uses the same Via headers as the request being cancelled"
    # 标准理解：客户端的 Via 头相同（branch 参数相同），代理可以添加不同的 Via branch
    # 但 Zoiper 2.x 要求整个 Via 栈都匹配，因此需要复用 INVITE 的 branch
    if method != "ACK":
        # 获取 Call-ID
        call_id = msg.get("call-id")
        
        # 为 CANCEL 复用对应 INVITE 的 branch
        if method == "CANCEL" and call_id and call_id in INVITE_BRANCHES:
            branch = INVITE_BRANCHES[call_id]
            log.debug(f"[CANCEL] Reusing INVITE branch: {branch} for Call-ID: {call_id}")
        else:
            # 其他请求生成新的 branch
            branch = f"z9hG4bK-{gen_tag(10)}"
            # 如果是 INVITE，保存 branch 供后续 CANCEL 使用
            if method == "INVITE" and call_id:
                INVITE_BRANCHES[call_id] = branch
                log.debug(f"[INVITE] Saved branch: {branch} for Call-ID: {call_id}")
        
        _add_top_via(msg, branch)

        # 如果没有 Max-Forwards、CSeq 等关键头，给个兜底（少见）
        _ensure_header(msg, "cseq", "1 " + method)
        _ensure_header(msg, "from", msg.get("from") or "<sip:unknown@localhost>;tag=" + gen_tag())
        _ensure_header(msg, "to", msg.get("to") or "<sip:unknown@localhost>")
        _ensure_header(msg, "call-id", msg.get("call-id") or gen_tag() + "@localhost")
        _ensure_header(msg, "via", f"SIP/2.0/UDP {SERVER_IP}:{SERVER_PORT};branch={branch};rport")
    else:
        # ACK 请求：无状态转发，不修改 Via 和其他头域
        log.debug(f"[ACK-STATELESS] Forwarding ACK without adding Via (stateless proxy mode)")

    # 确定下一跳：优先 Route，否则用 Request-URI
    next_hop = None
    routes = msg.headers.get("route", [])
    
    # 如果是已知对话的请求，且有 Route 头，弹出我们的 Route
    if call_id in DIALOGS and routes:
        log.debug(f"[ROUTE] In-dialog request with {len(routes)} Route headers")
        _strip_our_top_route_and_get_next(msg)
        routes = msg.headers.get("route", [])
    
    if routes:
        # 取首个 Route 的 URI
        r = routes[0]
        if "<" in r and ">" in r:
            ruri = r[r.find("<")+1:r.find(">")]
        else:
            ruri = r.split(":", 1)[-1]
        nh = _host_port_from_sip_uri(ruri)
        next_hop = nh
        log.debug(f"[ROUTE] Using Route header: {ruri} -> {next_hop}")
    else:
        # 用 Request-URI
        ruri = msg.start_line.split()[1]
        next_hop = _host_port_from_sip_uri(ruri)
        log.debug(f"[ROUTE] Using Request-URI: {ruri} -> {next_hop}")

    if not next_hop or next_hop == ("", 0):
        resp = _make_response(msg, 502, "Bad Gateway")
        transport.sendto(resp.to_bytes(), addr)
        log.tx(addr, resp.start_line, extra="no next hop")
        return

    host, port = next_hop
    
    # 如果是已知对话的请求且检测到环路，尝试从 REG_BINDINGS 获取正确的目标
    is_in_dialog = call_id and call_id in DIALOGS if 'call_id' in locals() else False
    
    # === 🔒 防止自环 ===
    # 注意：ACK 请求的 R-URI 可能是 sip:user@127.0.0.1，会被误判为环路
    # 所以需要检查是否是真正的环路（明确指定了端口 5060）
    if (host == SERVER_IP and port == SERVER_PORT):
        # 如果是已知对话的请求且目标指向服务器，尝试使用注册表中的地址
        if is_in_dialog:
            try:
                to_aor = _aor_from_to(msg.get("to")) or msg.start_line.split()[1]
                targets = REG_BINDINGS.get(to_aor, [])
                if targets:
                    b_uri = targets[0]["contact"]
                    real_host, real_port = _host_port_from_sip_uri(b_uri)
                    if real_host and real_port and (real_host != SERVER_IP or real_port != SERVER_PORT):
                        host, port = real_host, real_port
                        log.debug(f"[IN-DIALOG] Using contact address from REG_BINDINGS: {host}:{port}")
                    else:
                        log.drop(f"[IN-DIALOG] Loop detected and no valid contact, skipping: {host}:{port}")
                        return
                else:
                    log.drop(f"[IN-DIALOG] Loop detected and no bindings for AOR {to_aor}, skipping: {host}:{port}")
                    return
            except Exception as e:
                log.warning(f"[IN-DIALOG] Loop check failed: {e}")
                log.drop(f"Loop detected: skipping self-forward to {host}:{port}")
                return
        # 如果是 ACK，处理取决于 ACK 类型
        elif method == "ACK":
            # 非 2xx ACK：使用 DIALOGS 找到被叫地址
            # RFC 3261: 非 2xx ACK 的 R-URI 必须和原始 INVITE 相同，不能修改
            # 但服务器需要知道转发给谁（被叫）
            if not is_2xx_ack:
                log.debug(f"[ACK-NON2XX] Non-2xx ACK detected, using DIALOGS to find target")
                # 从 DIALOGS 获取被叫地址
                if call_id and call_id in DIALOGS:
                    caller_addr, callee_addr = DIALOGS[call_id]
                    host, port = callee_addr
                    log.debug(f"[ACK-NON2XX] Routing to callee: {host}:{port}")
                else:
                    log.warning(f"[ACK-NON2XX] Call-ID {call_id} not in DIALOGS, cannot route")
                    return
            else:
                # 2xx ACK：尝试使用注册表中的 contact 地址
                try:
                    to_aor = _aor_from_to(msg.get("to"))
                    ruri = msg.start_line.split()[1]
                    log.debug(f"[ACK-2XX-CHECK] To AOR: {to_aor} | R-URI: {ruri} | Detected loop: {host}:{port}")
                    
                    if to_aor:
                        targets = REG_BINDINGS.get(to_aor, [])
                        if targets:
                            b_uri = targets[0]["contact"]
                            real_host, real_port = _host_port_from_sip_uri(b_uri)
                            if real_host and real_port:
                                host, port = real_host, real_port
                                log.debug(f"ACK (2xx) using contact address: {b_uri} -> {host}:{port}")
                            else:
                                log.drop(f"ACK (2xx) loop detected: skipping self-forward to {host}:{port}")
                                return
                    else:
                        log.warning(f"ACK (2xx): No To AOR found, R-URI: {ruri}")
                        log.drop(f"ACK (2xx) loop detected: skipping self-forward to {host}:{port}")
                        return
                except Exception as e:
                    log.warning(f"ACK (2xx) loop check failed: {e}")
                    log.drop(f"Loop detected: skipping self-forward to {host}:{port}")
                    return
        else:
            log.drop(f"Loop detected: skipping self-forward to {host}:{port}")
        return

    # --- NAT/私网修正: 如果 Contact 或 R-URI 的 host 不可达，强制使用我们已知的绑定地址 ---
    # 从 REG_BINDINGS 查找被叫实际的 contact IP
    # 注意：ACK 已经在环路检测中使用了 contact 地址，这里跳过避免重复处理
    if method in ("INVITE", "BYE", "CANCEL", "UPDATE", "PRACK", "MESSAGE", "REFER", "NOTIFY", "SUBSCRIBE"):
        try:
            aor = _aor_from_to(msg.get("to")) or msg.start_line.split()[1]
            bindings = REG_BINDINGS.get(aor, [])
            if bindings:
                # 取第一个绑定的 contact，解析 IP 和端口
                b_uri = bindings[0]["contact"]
                real_host, real_port = _host_port_from_sip_uri(b_uri)
                host, port = real_host, real_port
                log.debug(f"[{method}] Using registered contact: {b_uri} -> {host}:{port}")
            else:
                # 没有找到注册绑定，回复 480 Temporarily Unavailable
                if method in ("MESSAGE", "REFER", "NOTIFY", "SUBSCRIBE"):
                    log.warning(f"[{method}] No bindings found for AOR: {aor}")
                    resp = _make_response(msg, 480, "Temporarily Unavailable")
                    transport.sendto(resp.to_bytes(), addr)
                    log.tx(addr, resp.start_line, extra=f"aor={aor}")
                    return
        except Exception as e:
            log.warning(f"NAT fix skipped: {e}")
    # -------------------------------------------------------------------------------

    try:
        # 详细日志：显示发送前的消息详情
        call_id = msg.get("call-id")
        vias = msg.headers.get("via", [])
        routes = msg.headers.get("route", [])
        log.debug(f"[FWD-DETAIL] Method: {method} | Call-ID: {call_id} | Target: {host}:{port} | Via hops: {len(vias)} | Route: {len(routes)}")
        
        transport.sendto(msg.to_bytes(), (host, port))
        log.fwd(method, (host, port), f"R-URI={msg.start_line.split()[1]}")
        
        # 记录请求映射：Call-ID -> 原始请求发送者地址（用于响应转发）
        # 注意：这里记录的是 addr（请求发送者），而非 (host, port)（转发目标）
        call_id = msg.get("call-id")
        if call_id and method in ("INVITE", "BYE", "CANCEL", "UPDATE", "PRACK", "MESSAGE", "REFER", "NOTIFY", "SUBSCRIBE"):
            PENDING_REQUESTS[call_id] = addr  # 记录请求发送者地址
            # 记录对话信息：主叫和被叫地址
            if method == "INVITE":
                DIALOGS[call_id] = (addr, (host, port))
                
                # 解析 SDP 提取呼叫类型和编解码信息
                call_type, codec = extract_sdp_info(msg.body)
                
                # CDR: 记录呼叫开始
                cdr.record_call_start(
                    call_id=call_id,
                    caller_uri=msg.get("from") or "",
                    callee_uri=msg.get("to") or "",
                    caller_addr=addr,
                    callee_ip=host,
                    callee_port=port,
                    call_type=call_type,
                    codec=codec,
                    user_agent=msg.get("user-agent") or "",
                    cseq=msg.get("cseq") or "",
                    server_ip=SERVER_IP,
                    server_port=SERVER_PORT
                )
            elif method == "BYE":
                # CDR: 记录呼叫结束（只在第一次收到 BYE 时记录，避免重传导致重复）
                # 通过检查 DIALOGS 是否存在来判断是否是第一次
                if call_id in DIALOGS:
                    cdr.record_call_end(
                        call_id=call_id,
                        termination_reason="Normal",
                        cseq=msg.get("cseq") or ""
                    )
            elif method == "CANCEL":
                # CDR: 记录呼叫取消（只在第一次收到时记录）
                if call_id in DIALOGS:
                    cdr.record_call_cancel(
                        call_id=call_id,
                        cseq=msg.get("cseq") or ""
                    )
            elif method == "MESSAGE":
                # CDR: 记录短信（MESSAGE 一般不会重传，但为了统一性也加上检查）
                # 使用 CSeq 作为唯一性标识，防止重复记录
                message_id = f"{call_id}-{msg.get('cseq') or ''}"
                # MESSAGE 请求不在 DIALOGS 中，所以直接记录（CDR 层面会防重复）
                cdr.record_message(
                    call_id=message_id,  # 使用 call_id+cseq 作为唯一标识
                    caller_uri=msg.get("from") or "",
                    callee_uri=msg.get("to") or "",
                    caller_addr=addr,
                    message_body=msg.body.decode('utf-8', errors='ignore') if msg.body else "",
                    user_agent=msg.get("user-agent") or "",
                    cseq=msg.get("cseq") or "",
                    server_ip=SERVER_IP,
                    server_port=SERVER_PORT
                )
        # ACK 也需要记录地址（虽然不需要响应，但保留追踪）
        elif call_id and method == "ACK":
            PENDING_REQUESTS[call_id] = addr  # 记录请求发送者地址
            
    except OSError as e:
        # 网络错误：目标主机不可达
        # errno 65: No route to host (macOS/BSD)
        # errno 113: No route to host (Linux)
        # errno 101: Network is unreachable
        if e.errno in (65, 113, 101):
            log.warning(f"[NETWORK] Target unreachable {host}:{port} - {e}")
            # 根据方法类型返回适当的错误响应
            if method in ("INVITE", "MESSAGE", "REFER", "NOTIFY", "SUBSCRIBE"):
                # 对于需要响应的请求，返回 480 Temporarily Unavailable
                resp = _make_response(msg, 480, "Temporarily Unavailable")
                transport.sendto(resp.to_bytes(), addr)
                log.tx(addr, resp.start_line, extra=f"target unreachable")
            elif method == "BYE":
                # BYE 失败，返回 408 Request Timeout
                resp = _make_response(msg, 408, "Request Timeout")
                transport.sendto(resp.to_bytes(), addr)
                log.tx(addr, resp.start_line, extra=f"target unreachable")
                
                # 清理 DIALOGS，防止重传 BYE 时重复记录 CDR
                if call_id and call_id in DIALOGS:
                    del DIALOGS[call_id]
                    log.debug(f"[DIALOG-CLEANUP] Cleaned up unreachable call: {call_id}")
            # ACK 和 CANCEL 不需要响应
        else:
            # 其他网络错误
            log.error(f"[NETWORK] Send failed to {host}:{port} - {e}")
            resp = _make_response(msg, 503, "Service Unavailable")
            transport.sendto(resp.to_bytes(), addr)
            log.tx(addr, resp.start_line, extra=f"network error")
    except Exception as e:
        # 其他异常
        log.error(f"[ERROR] Forward failed: {e}")
        resp = _make_response(msg, 502, "Bad Gateway")
        transport.sendto(resp.to_bytes(), addr)
        log.tx(addr, resp.start_line, extra=f"forward error")

def _forward_response(resp: SIPMessage, addr, transport):
    """
    响应转发：
    - 如果顶层 Via 是我们，弹出它
    - 将响应发给新的顶层 Via 的 sent-by
    - 若 sent-by 不可达，则优先使用待处理的请求地址，其次用当前addr
    - 停止转发 482/482 等错误响应，避免环路
    """
    vias = resp.headers.get("via", [])
    if not vias:
        return

    # 检查顶层Via是否是我们
    top = vias[0]
    if f"{SERVER_IP}:{SERVER_PORT}" not in top:
        return
    
    # 如果是错误响应（如 482 Loop Detected），不应该继续转发
    # 这些响应应该直接返回给当前接收方
    status_code = resp.start_line.split()[1] if len(resp.start_line.split()) > 1 else ""
    if status_code in ("482", "483", "502", "503", "504"):
        call_id_resp = resp.get("call-id")
        vias_resp = resp.headers.get("via", [])
        log.warning(f"Dropping error response: {resp.start_line} | Call-ID: {call_id_resp} | Via hops: {len(vias_resp)}")
        # 打印 Via 头内容以便调试
        for i, via in enumerate(vias_resp):
            log.debug(f"  Via[{i}]: {via}")
        return

    # 修正响应中的 Contact 头：根据网络环境处理
    # 模式1：FORCE_LOCAL_ADDR=True（本机测试）- 强制使用 127.0.0.1
    # 模式2：FORCE_LOCAL_ADDR=False（真实网络）- 保持服务器可见地址
    contacts = resp.headers.get("contact", [])
    if contacts and FORCE_LOCAL_ADDR:
        for i, contact_val in enumerate(contacts):
            original = contact_val
            # 提取端口号
            port_match = re.search(r":(\d+)", contact_val)
            port = port_match.group(1) if port_match else "5060"
            
            # 替换所有外部 IP 为 127.0.0.1（仅在本机测试模式）
            # 保留 sip:user@host:port 的格式，只替换 host 部分
            contact_val = re.sub(r"@[^:;>]+", f"@127.0.0.1", contact_val)
            
            if contact_val != original:
                contacts[i] = contact_val
                log.debug(f"[CONTACT-FIX] Contact修正 (本机模式): {original} -> {contact_val}")
        resp.headers["contact"] = contacts
    elif contacts:
        # 真实网络模式：检查是否需要 NAT 修正
        for i, contact_val in enumerate(contacts):
            # 如果 Contact 地址不在本地网络中，可能需要修正
            # 这里保持原样，让实际的网络环境处理
            pass

    # 弹出我们的 Via
    _pop_top_via(resp)
    vias2 = resp.headers.get("via", [])
    if not vias2:
        return  # 无上层Via，无法继续转发

    # 从新的顶层Via中取目标
    nhost, nport = _host_port_from_via(vias2[0])
    log.debug(f"[RESP-ROUTE] Via头数量: {len(vias2)}, Via[0]: {vias2[0]}")
    log.debug(f"[RESP-ROUTE] Via解析结果 -> target: {nhost}:{nport}")

    # 获取Call-ID，用于查找原始请求发送者地址
    call_id = resp.get("call-id")
    original_sender_addr = PENDING_REQUESTS.get(call_id) if call_id else None
    log.debug(f"[RESP-ROUTE] Call-ID: {call_id}, Original sender: {original_sender_addr}, Via解析: {nhost}:{nport}")

    # NAT修正：根据网络环境判断
    is_local_network = (
        nhost == "127.0.0.1" or 
        nhost.startswith(("192.168.", "10.", "172.")) or 
        nhost in ("localhost", SERVER_IP) or
        nhost in LOCAL_NETWORKS
    )
    
    if not is_local_network:
        # Via 头包含外部/公网地址，使用原始请求发送者地址
        if original_sender_addr:
            log.debug(f"[RESP-NAT] Via指向外部地址 {nhost}:{nport}, 使用原始发送者: {original_sender_addr}")
            nhost, nport = original_sender_addr
        else:
            # 回退到REGISTER绑定地址
            for aor, binds in REG_BINDINGS.items():
                for b in binds:
                    host2, port2 = _host_port_from_sip_uri(b["contact"])
                    if (host2, port2) != (addr[0], addr[1]):  # 避免回环
                        nhost, nport = host2, port2
                        log.debug(f"[RESP-NAT] 使用绑定地址: {host2}:{port2}")
                        break

    # 兜底：如果还是没找到，就用当前addr（收到响应的对端）
    if not nhost or not nport:
        nhost, nport = addr
        log.debug(f"Using fallback address: {addr}")

    # 防止自环
    if (nhost == SERVER_IP and nport == SERVER_PORT):
        log.drop(f"Prevented response loop to self ({nhost}:{nport})")
        return

    # 检查是否是 INVITE 的最终响应
    # 只有 INVITE 的响应需要特殊路由到主叫（因为可能有 NAT 问题）
    # 其他请求（BYE, CANCEL, UPDATE）的响应应该按 Via 头路由
    status_code = resp.start_line.split()[1] if len(resp.start_line.split()) > 1 else ""
    cseq_header = resp.get("cseq") or ""
    is_invite_response = "INVITE" in cseq_header
    
    if call_id in DIALOGS and is_invite_response:
        caller_addr, callee_addr = DIALOGS[call_id]
        log.debug(f"[DIALOG-ROUTE] INVITE response: caller={caller_addr}, callee={callee_addr}, status={status_code}")
        # INVITE 的最终响应应该发给主叫（发起 INVITE 的一方）
        if status_code in ("200", "486", "487", "488", "600", "603", "604"):
            nhost, nport = caller_addr
            log.debug(f"Final INVITE response {status_code} to caller: {caller_addr} (overriding Via route)")
    elif call_id in DIALOGS:
        # 非 INVITE 响应（如 BYE, CANCEL）：按 Via 头路由，不覆盖
        caller_addr, callee_addr = DIALOGS[call_id]
        log.debug(f"[DIALOG-ROUTE] Non-INVITE response ({cseq_header}): using Via route to {nhost}:{nport}")

    try:
        transport.sendto(resp.to_bytes(), (nhost, nport))
        log.fwd(f"RESP {resp.start_line}", (nhost, nport))
        
        # 清理追踪记录
        # 注意：2xx 响应(200)不立即清理 DIALOGS，因为还需要等 ACK
        # 只清理失败响应(486, 487等)
        # CDR: 只在第一次清理时记录（避免重传导致重复记录）
        need_cleanup = False
        if status_code in ("486", "487", "488", "600", "603", "604"):
            if call_id in DIALOGS:
                need_cleanup = True  # 第一次收到最终响应
            if call_id in PENDING_REQUESTS:
                del PENDING_REQUESTS[call_id]
            if call_id in DIALOGS:
                del DIALOGS[call_id]
                log.debug(f"[DIALOG-CLEANUP] Cleaned up failed call: {call_id}")
            # 清理 INVITE branch 追踪
            if call_id in INVITE_BRANCHES:
                del INVITE_BRANCHES[call_id]
                log.debug(f"[BRANCH-CLEANUP] Cleaned up INVITE branch: {call_id}")
        
        # CDR: 记录呼叫应答和呼叫失败（只在第一次收到响应时记录，避免重传导致重复）
        if is_invite_response:
            if status_code == "200":
                # 解析 200 OK 响应中的 SDP（被叫可能使用不同的编解码）
                call_type_answer, codec_answer = extract_sdp_info(resp.body)
                
                # CDR: 记录呼叫应答
                cdr.record_call_answer(
                    call_id=call_id,
                    callee_addr=addr,
                    call_type=call_type_answer if call_type_answer else None,
                    codec=codec_answer if codec_answer else None,
                    status_code=200,
                    status_text="OK"
                )
            elif need_cleanup:
                # CDR: 记录呼叫失败（仅在第一次清理时记录）
                status_text = resp.start_line.split(maxsplit=2)[2] if len(resp.start_line.split(maxsplit=2)) > 2 else "Failed"
                cdr.record_call_fail(
                    call_id=call_id,
                    status_code=int(status_code),
                    status_text=status_text,
                    reason=f"{status_code} {status_text}"
                )
            elif status_code.startswith(('4', '5', '6')) and status_code not in ("100", "180", "183", "486", "487", "488", "600", "603", "604"):
                # CDR: 记录其他失败响应（如 480, 404 等）
                # 只有当 call_id 还在 DIALOGS 中时才记录（第一次）
                if call_id in DIALOGS:
                    status_text = resp.start_line.split(maxsplit=2)[2] if len(resp.start_line.split(maxsplit=2)) > 2 else "Error"
                    cdr.record_call_fail(
                        call_id=call_id,
                        status_code=int(status_code),
                        status_text=status_text,
                        reason=f"{status_code} {status_text}"
                    )
                    # 立即清理，避免重复记录
                    if call_id in PENDING_REQUESTS:
                        del PENDING_REQUESTS[call_id]
                    if call_id in DIALOGS:
                        del DIALOGS[call_id]
                    if call_id in INVITE_BRANCHES:
                        del INVITE_BRANCHES[call_id]
        elif status_code == "200":
            # 200 OK：需要区分不同场景
            # - INVITE 200 OK：已在上面处理（保留 DIALOGS 等待 ACK）
            # - BYE 200 OK：应该清理 DIALOGS（呼叫已结束）
            # - 其他方法 200 OK：与 DIALOGS 无关
            if "BYE" in cseq_header and call_id in DIALOGS:
                # BYE 200 OK：清理 dialog
                del DIALOGS[call_id]
                log.debug(f"[DIALOG-CLEANUP] Cleaned up dialog after BYE: {call_id}")
            # 清理其他追踪数据
            if call_id in PENDING_REQUESTS:
                del PENDING_REQUESTS[call_id]
            if call_id in INVITE_BRANCHES:
                del INVITE_BRANCHES[call_id]
                log.debug(f"[BRANCH-CLEANUP] Cleaned up INVITE branch after 200 OK: {call_id}")
    except OSError as e:
        # UDP发送错误 - 尝试备用地址
        log.error(f"UDP send failed to ({nhost}:{nport}): {e}")
        
        # 如果目标地址失败，尝试使用原始发送者地址
        if original_sender_addr and (nhost, nport) != original_sender_addr:
            try:
                transport.sendto(resp.to_bytes(), original_sender_addr)
                log.fwd(f"RESP {resp.start_line} (retry)", original_sender_addr)
            except Exception as e2:
                log.error(f"Retry also failed: {e2}")
    except Exception as e:
        log.error(f"forward resp failed: {e}")


def on_datagram(data: bytes, addr, transport):
    # 忽略 UA keepalive 空包
    if not data or data.strip() in (b"", b"\r\n", b"\r\n\r\n"):
        return
    try:
        msg = parse(data)
        is_req = _is_request(msg.start_line)
        
        # 详细日志：显示 Call-ID, To tag, Via 头
        call_id = msg.get("call-id")
        to_val = msg.get("to")
        vias = msg.headers.get("via", [])
        
        if is_req:
            method = _method_of(msg)
            log.info(f"[RX] {addr} -> {msg.start_line} | Call-ID: {call_id} | To tag: {'YES' if 'tag=' in (to_val or '') else 'NO'} | Via: {len(vias)} hops")
        else:
            status = msg.start_line.split()[1] if len(msg.start_line.split()) > 1 else ""
            log.info(f"[RX] {addr} -> {msg.start_line} | Call-ID: {call_id} | Via: {len(vias)} hops")
        
        log.rx(addr, msg.start_line)
        if is_req:
            method = _method_of(msg)
            if method == "OPTIONS":
                resp = _make_response(msg, 200, "OK", extra_headers={
                    "accept": "application/sdp",
                    "supported": "100rel, timer, path"
                })
                transport.sendto(resp.to_bytes(), addr)
                log.tx(addr, resp.start_line)
                # CDR: 记录 OPTIONS 请求（心跳/能力查询）
                cdr.record_options(
                    caller_uri=msg.get("from") or "",
                    callee_uri=msg.get("to") or "",
                    caller_addr=addr,
                    call_id=call_id or "",
                    user_agent=msg.get("user-agent") or "",
                    cseq=msg.get("cseq") or ""
                )
            elif method == "REGISTER":
                handle_register(msg, addr, transport)
            elif method in ("INVITE", "BYE", "CANCEL", "PRACK", "UPDATE", "REFER", "NOTIFY", "SUBSCRIBE", "MESSAGE", "ACK"):
                _forward_request(msg, addr, transport)
            else:
                resp = _make_response(msg, 405, "Method Not Allowed")
                transport.sendto(resp.to_bytes(), addr)
                log.tx(addr, resp.start_line)
        else:
            # 响应：转发
            _forward_response(msg, addr, transport)

    except Exception as e:
        log.error(f"parse/send failed: {e}")

async def main():
    # 启动 MML 管理界面
    try:
        from web.mml_server import init_mml_interface
        # 传递服务器全局状态给 MML 界面
        server_globals = {
            'SERVER_IP': SERVER_IP,
            'SERVER_PORT': SERVER_PORT,
            'FORCE_LOCAL_ADDR': FORCE_LOCAL_ADDR,
            'REGISTRATIONS': REG_BINDINGS,  # 实际变量名是 REG_BINDINGS
            'DIALOGS': DIALOGS,
            'PENDING_REQUESTS': PENDING_REQUESTS,
            'INVITE_BRANCHES': INVITE_BRANCHES,
        }
        init_mml_interface(port=8888, server_globals=server_globals)
    except Exception as e:
        log.warning(f"MML interface failed to start: {e}")
    
    # 创建 UDP 服务器
    udp = UDPServer((SERVER_IP, SERVER_PORT), on_datagram)
    await udp.start()
    # UDP server listening 日志已在 transport_udp.py 中输出，此处不再重复
    
    # 创建并启动定时器
    timers = create_timers(log)
    await timers.start(
        pending_requests=PENDING_REQUESTS,
        dialogs=DIALOGS,
        invite_branches=INVITE_BRANCHES,
        reg_bindings=REG_BINDINGS
    )
    
    try:
        # 等待服务器运行
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        log.info("Shutting down server...")
    finally:
        # 停止定时器
        await timers.stop()

if __name__ == "__main__":
    asyncio.run(main())


