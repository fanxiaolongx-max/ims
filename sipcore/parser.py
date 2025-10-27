# sipcore/parser.py
from .message import SIPMessage, CRLF

def parse(raw: bytes) -> SIPMessage:
    head, sep, body = raw.partition(b"\r\n\r\n")
    head_str = head.decode(errors="ignore")
    lines = head_str.split(CRLF)
    if not lines or lines[0].strip() == "":
        raise ValueError("Invalid SIP start line")

    start = lines[0]
    headers = {}
    cur = None
    for line in lines[1:]:
        if line == "":
            break
        if (line.startswith(" ") or line.startswith("\t")) and cur:
            headers[cur][-1] += " " + line.strip()
        else:
            if ":" not in line:
                continue
            name, val = line.split(":", 1)
            name_l = name.lower()
            headers.setdefault(name_l, []).append(val.strip())
            cur = name_l
    return SIPMessage(start_line=start, headers=headers, body=body)
