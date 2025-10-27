# sipcore/message.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

CRLF = "\r\n"

@dataclass
class SIPMessage:
    start_line: str
    headers: Dict[str, List[str]] = field(default_factory=dict)
    body: bytes = b""

    def get(self, name: str) -> Optional[str]:
        vals = self.headers.get(name.lower())
        return vals[0] if vals else None

    def add_header(self, name: str, value: str):
        self.headers.setdefault(name.lower(), []).append(value)

    # def to_bytes(self) -> bytes:
    #     lines = [self.start_line]
    #     for k, vs in self.headers.items():
    #         for v in vs:
    #             lines.append(f"{self._canon(k)}: {v}")
    #     lines.append("")  # empty line before body
    #     head = (CRLF.join(lines)).encode()
    #     return head + (self.body or b"")

    def to_bytes(self) -> bytes:
        lines = [self.start_line]
        for k, vs in self.headers.items():
            for v in vs:
                lines.append(f"{self._canon(k)}: {v}")
        # Header 部分结尾要加两个 CRLF：一个 join 的结尾 + 一个额外空行
        data = CRLF.join(lines) + CRLF * 2
        return data.encode() + (self.body or b"")

    @staticmethod
    def _canon(k: str) -> str:
        return "-".join(p.capitalize() for p in k.split("-"))
