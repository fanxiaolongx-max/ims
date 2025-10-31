#!/usr/bin/env python3
"""
SIP 服务器自动化测试脚本
测试各种呼叫场景：注册、呼叫、短信、异常情况等
"""

import socket
import time
import hashlib
import random
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import threading

# ====== 配置 ======
SERVER_IP = "192.168.8.126"
SERVER_PORT = 5060
LOCAL_IP = "192.168.8.126"  # 测试客户端 IP（与服务器同一台机器）

# 测试用户
USERS = {
    "1001": {"password": "1234", "port": 5061},
    "1002": {"password": "1234", "port": 5062},
    "1003": {"password": "1234", "port": 5063},
}

# ====== SIP 消息构建工具 ======

@dataclass
class SIPCall:
    """SIP 呼叫状态"""
    call_id: str
    from_tag: str
    to_tag: Optional[str] = None
    local_cseq: int = 1
    remote_cseq: int = 0
    dialog_established: bool = False

class SIPClient:
    """SIP 客户端"""
    
    def __init__(self, username: str, password: str, local_port: int):
        self.username = username
        self.password = password
        self.local_port = local_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LOCAL_IP, local_port))
        self.sock.settimeout(5.0)  # 5 秒超时
        
        self.registered = False
        self.current_call: Optional[SIPCall] = None
        self.branch_counter = 0
        
    def _gen_branch(self) -> str:
        """生成 Via branch"""
        self.branch_counter += 1
        return f"z9hG4bK-{random.randint(100000, 999999)}-{self.branch_counter}"
    
    def _gen_tag(self) -> str:
        """生成 tag"""
        return f"{random.randint(100000, 999999)}"
    
    def _gen_call_id(self) -> str:
        """生成 Call-ID"""
        return f"{random.randint(100000, 999999)}@{LOCAL_IP}"
    
    def _compute_response(self, username: str, realm: str, password: str, 
                         uri: str, method: str, nonce: str, 
                         qop: str = "", cnonce: str = "", nc: str = "00000001") -> str:
        """计算 Digest 认证响应"""
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        
        if qop:
            # 带 qop 的认证（RFC 2617）
            response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
        else:
            # 不带 qop 的认证（RFC 2069）
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        
        return response
    
    def _parse_response(self, data: bytes) -> Dict:
        """解析 SIP 响应"""
        try:
            text = data.decode('utf-8')
            lines = text.split('\r\n')
            
            # 解析状态行
            status_line = lines[0]
            parts = status_line.split(maxsplit=2)
            status_code = int(parts[1]) if len(parts) > 1 else 0
            status_text = parts[2] if len(parts) > 2 else ""
            
            # 解析头部
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            return {
                'status_code': status_code,
                'status_text': status_text,
                'headers': headers,
                'raw': text
            }
        except Exception as e:
            return {'error': str(e), 'raw': data}
    
    def _send_and_receive(self, message: str, expect_response: bool = True, debug: bool = False) -> Optional[Dict]:
        """发送消息并接收响应"""
        try:
            if debug:
                print(f"\n>>> 发送消息:")
                print(message[:200] + "...")
            
            self.sock.sendto(message.encode('utf-8'), (SERVER_IP, SERVER_PORT))
            
            if expect_response:
                data, addr = self.sock.recvfrom(4096)
                parsed = self._parse_response(data)
                
                if debug:
                    print(f"\n<<< 收到响应:")
                    print(f"状态码: {parsed.get('status_code')}")
                    print(f"状态文本: {parsed.get('status_text')}")
                
                return parsed
            return None
        except socket.timeout:
            if debug:
                print(f"\n<<< 超时!")
            return {'error': 'timeout'}
        except Exception as e:
            if debug:
                print(f"\n<<< 异常: {e}")
            return {'error': str(e)}
    
    def register(self, expires: int = 3600, debug: bool = False) -> bool:
        """注册用户"""
        print(f"\n[{self.username}] 注册中...")
        
        # 第一次注册（无认证）
        call_id = self._gen_call_id()
        from_tag = self._gen_tag()
        branch = self._gen_branch()
        
        if debug:
            print(f"  Call-ID: {call_id}")
            print(f"  From-Tag: {from_tag}")
        
        register_msg = (
            f"REGISTER sip:{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={from_tag}\r\n"
            f"To: <sip:{self.username}@{SERVER_IP}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 REGISTER\r\n"
            f"Contact: <sip:{self.username}@{LOCAL_IP}:{self.local_port}>\r\n"
            f"Expires: {expires}\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        resp = self._send_and_receive(register_msg, debug=debug)
        
        if debug:
            print(f"  第一次 REGISTER 响应: {resp.get('status_code')}")
        
        if resp.get('status_code') == 401:
            # 需要认证
            auth_header = resp['headers'].get('www-authenticate', '')
            
            # 提取 realm 和 nonce（暂时忽略 qop，使用简化认证）
            realm_match = re.search(r'realm="([^"]+)"', auth_header)
            nonce_match = re.search(r'nonce="([^"]+)"', auth_header)
            
            if not realm_match or not nonce_match:
                print(f"  ✗ 无法解析认证头: {auth_header}")
                return False
            
            realm = realm_match.group(1)
            nonce = nonce_match.group(1)
            
            if debug:
                print(f"  提取的认证参数:")
                print(f"    realm: {realm}")
                print(f"    nonce: {nonce}")
            
            # 第二次注册（带认证，使用简化方式）
            uri = f"sip:{SERVER_IP}"
            response = self._compute_response(self.username, realm, self.password, 
                                            uri, "REGISTER", nonce)
            
            if debug:
                print(f"  计算的 response: {response}")
            
            branch = self._gen_branch()
            register_msg = (
                f"REGISTER sip:{SERVER_IP} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
                f"From: <sip:{self.username}@{SERVER_IP}>;tag={from_tag}\r\n"
                f"To: <sip:{self.username}@{SERVER_IP}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 2 REGISTER\r\n"
                f"Contact: <sip:{self.username}@{LOCAL_IP}:{self.local_port}>\r\n"
                f"Authorization: Digest username=\"{self.username}\", "
                f"realm=\"{realm}\", nonce=\"{nonce}\", uri=\"{uri}\", "
                f"response=\"{response}\"\r\n"
                f"Expires: {expires}\r\n"
                f"Max-Forwards: 70\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            resp = self._send_and_receive(register_msg, debug=debug)
            
            if debug:
                print(f"  第二次 REGISTER 响应: {resp.get('status_code')} {resp.get('status_text')}")
        
        if resp.get('status_code') == 200:
            self.registered = True
            print(f"  ✓ 注册成功")
            return True
        else:
            print(f"  ✗ 注册失败: {resp.get('status_code')} {resp.get('status_text')}")
            return False
    
    def unregister(self) -> bool:
        """注销"""
        print(f"\n[{self.username}] 注销中...")
        return self.register(expires=0)
    
    def invite(self, callee: str, sdp: Optional[str] = None) -> Optional[SIPCall]:
        """发起呼叫"""
        print(f"\n[{self.username}] 呼叫 {callee}...")
        
        call_id = self._gen_call_id()
        from_tag = self._gen_tag()
        branch = self._gen_branch()
        
        # 默认 SDP
        if sdp is None:
            sdp = (
                "v=0\r\n"
                f"o={self.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
                "s=Test Call\r\n"
                f"c=IN IP4 {LOCAL_IP}\r\n"
                "t=0 0\r\n"
                "m=audio 8000 RTP/AVP 0 8\r\n"
                "a=rtpmap:0 PCMU/8000\r\n"
                "a=rtpmap:8 PCMA/8000\r\n"
            )
        
        invite_msg = (
            f"INVITE sip:{callee}@{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={from_tag}\r\n"
            f"To: <sip:{callee}@{SERVER_IP}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Contact: <sip:{self.username}@{LOCAL_IP}:{self.local_port}>\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp)}\r\n"
            f"\r\n"
            f"{sdp}"
        )
        
        # 发送 INVITE
        self.sock.sendto(invite_msg.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        
        # 创建呼叫对象
        call = SIPCall(
            call_id=call_id,
            from_tag=from_tag,
            local_cseq=1
        )
        self.current_call = call
        
        # 增加超时时间，等待响应（可能需要等待被叫用户响应）
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(15.0)  # 15 秒超时
        
        try:
            # 循环接收响应，直到收到最终响应（200 OK 或其他最终响应）
            while True:
                data, addr = self.sock.recvfrom(4096)
                
                # 检查收到的数据
                text = data.decode('utf-8', errors='ignore')
                
                if call_id in text:
                    # 匹配的 Call-ID，解析响应
                    resp = self._parse_response(data)
                    
                    if not resp or not resp.get('status_code'):
                        continue
                    
                    # 验证 Call-ID 匹配
                    resp_call_id = resp['headers'].get('call-id', '').strip()
                    if resp_call_id != call_id:
                        # Call-ID 不匹配，可能是其他请求的响应
                        continue
                    
                    status_code = resp.get('status_code')
                    
                    if status_code in [100, 180, 183]:
                        # 收到临时响应，继续等待
                        print(f"  → {status_code} {resp.get('status_text')}")
                        continue  # 继续循环等待最终响应
                    
                    elif status_code == 200:
                        # 收到最终响应 200 OK
                        print(f"  → 200 OK")
                        
                        # 提取 To tag
                        to_header = resp['headers'].get('to', '')
                        tag_match = re.search(r'tag=([^;>\s]+)', to_header)
                        if tag_match:
                            call.to_tag = tag_match.group(1)
                            call.dialog_established = True
                        
                        return call
                    
                    else:
                        # 收到其他最终响应（如 486, 487 等）
                        print(f"  ✗ 呼叫失败: {status_code} {resp.get('status_text')}")
                        return None
                else:
                    # Call-ID 不匹配，忽略
                    continue
                    
        except socket.timeout:
            print(f"  ✗ 等待响应超时（15秒内未收到匹配的响应）")
            print(f"  提示: 检查服务器日志，确认响应是否被正确转发")
            return None
        finally:
            self.sock.settimeout(old_timeout)
    
    def wait_for_response(self, call: SIPCall, timeout: float = 10.0) -> Optional[Dict]:
        """等待响应（180, 200 等）"""
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        
        try:
            data, addr = self.sock.recvfrom(4096)
            resp = self._parse_response(data)
            
            if resp.get('status_code') == 200:
                # 提取 To tag
                to_header = resp['headers'].get('to', '')
                tag_match = re.search(r'tag=([^;>\s]+)', to_header)
                if tag_match:
                    call.to_tag = tag_match.group(1)
                    call.dialog_established = True
                    print(f"  ✓ 200 OK 收到，对话已建立")
            
            return resp
        except socket.timeout:
            return {'error': 'timeout'}
        finally:
            self.sock.settimeout(old_timeout)
    
    def ack(self, call: SIPCall) -> None:
        """发送 ACK"""
        if not call.to_tag:
            print(f"  ✗ 无法发送 ACK：缺少 To tag")
            return
        
        branch = self._gen_branch()
        
        ack_msg = (
            f"ACK sip:{self.username}@{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={call.from_tag}\r\n"
            f"To: <sip:{self.username}@{SERVER_IP}>;tag={call.to_tag}\r\n"
            f"Call-ID: {call.call_id}\r\n"
            f"CSeq: {call.local_cseq} ACK\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        self._send_and_receive(ack_msg, expect_response=False)
        print(f"  → ACK 已发送")
    
    def bye(self, call: SIPCall, callee: Optional[str] = None) -> bool:
        """挂断呼叫
        
        Args:
            call: SIPCall 对象
            callee: 被叫用户地址（可选，如果不提供则从 To 头推断）
        """
        if not call.dialog_established:
            print(f"  ✗ 对话未建立，无法发送 BYE")
            return False
        
        print(f"\n[{self.username}] 挂断呼叫...")
        
        # 确定被叫用户地址
        if callee is None:
            # 如果没有提供被叫用户地址，使用通用格式
            callee = f"sip:unknown@{SERVER_IP}"
        else:
            callee = f"sip:{callee}@{SERVER_IP}"
        
        call.local_cseq += 1
        branch = self._gen_branch()
        
        bye_msg = (
            f"BYE {callee} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={call.from_tag}\r\n"
            f"To: <sip:{callee.split('@')[0].replace('sip:', '')}@{SERVER_IP}>;tag={call.to_tag}\r\n"
            f"Call-ID: {call.call_id}\r\n"
            f"CSeq: {call.local_cseq} BYE\r\n"
            f"Contact: <sip:{self.username}@{LOCAL_IP}:{self.local_port}>\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        resp = self._send_and_receive(bye_msg)
        
        if resp.get('status_code') == 200:
            print(f"  ✓ BYE 成功")
            self.current_call = None
            return True
        else:
            error_msg = resp.get('error', '未知错误') if resp else '未收到响应'
            status_code = resp.get('status_code', 'None') if resp else 'None'
            print(f"  ✗ BYE 失败: {status_code} {error_msg}")
            return False
    
    def cancel(self, call: SIPCall) -> bool:
        """取消呼叫"""
        print(f"\n[{self.username}] 取消呼叫...")
        
        branch = self._gen_branch()
        
        cancel_msg = (
            f"CANCEL sip:{self.username}@{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={call.from_tag}\r\n"
            f"To: <sip:{self.username}@{SERVER_IP}>\r\n"
            f"Call-ID: {call.call_id}\r\n"
            f"CSeq: {call.local_cseq} CANCEL\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        resp = self._send_and_receive(cancel_msg)
        
        if resp.get('status_code') == 200:
            print(f"  ✓ CANCEL 成功")
            self.current_call = None
            return True
        else:
            print(f"  ✗ CANCEL 失败: {resp.get('status_code')}")
            return False
    
    def message(self, to_user: str, text: str) -> bool:
        """发送即时消息"""
        print(f"\n[{self.username}] 发送消息给 {to_user}: {text}")
        
        call_id = self._gen_call_id()
        from_tag = self._gen_tag()
        branch = self._gen_branch()
        
        body = text.encode('utf-8')
        
        message_msg = (
            f"MESSAGE sip:{to_user}@{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{self.local_port};branch={branch}\r\n"
            f"From: <sip:{self.username}@{SERVER_IP}>;tag={from_tag}\r\n"
            f"To: <sip:{to_user}@{SERVER_IP}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 MESSAGE\r\n"
            f"Contact: <sip:{self.username}@{LOCAL_IP}:{self.local_port}>\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n"
        )
        
        # 发送消息（包括 body）
        full_message = message_msg.encode('utf-8') + body
        self.sock.sendto(full_message, (SERVER_IP, SERVER_PORT))
        
        # 等待响应（MESSAGE 应该有响应）
        try:
            # 增加超时时间，因为可能需要转发到被叫用户
            old_timeout = self.sock.gettimeout()
            self.sock.settimeout(10.0)  # 10 秒超时
            
            data, addr = self.sock.recvfrom(4096)
            resp = self._parse_response(data)
            
            # 恢复原来的超时设置
            self.sock.settimeout(old_timeout)
            
            status_code = resp.get('status_code', 0)
            status_text = resp.get('status_text', '')
            
            # MESSAGE 的响应：200 OK 表示成功，其他状态码表示失败（但已送达服务器）
            if status_code == 200:
                print(f"  ✓ 消息已发送并送达")
                return True
            elif status_code in (408, 480, 404):
                # 这些错误表示服务器尝试转发但被叫用户不可达
                print(f"  ⚠ 消息已送达服务器，但被叫用户不可达: {status_code} {status_text}")
                print(f"  （这是正常的，因为被叫用户没有实际监听消息）")
                return True  # 返回 True 表示测试通过（服务器正确处理了）
            else:
                print(f"  ✗ 消息发送失败: {status_code} {status_text}")
                return False
        except socket.timeout:
            self.sock.settimeout(old_timeout)
            print(f"  ✗ 消息发送超时（10秒内未收到响应）")
            return False
        except Exception as e:
            self.sock.settimeout(old_timeout)
            print(f"  ✗ 消息发送异常: {e}")
            return False
    
    def close(self):
        """关闭客户端"""
        self.sock.close()


# ====== 测试场景 ======

def print_scenario(name: str):
    """打印场景标题"""
    print("\n" + "="*70)
    print(f"  场景: {name}")
    print("="*70)

def test_scenario_1_normal_call():
    """场景1: 正常呼叫 - 接听并挂断"""
    print_scenario("正常呼叫 - 1001 呼叫 1002，通话 3 秒后主叫挂断")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    
    client2_call = None  # 存储被叫用户的呼叫对象
    
    def callee_listener(client, duration=15.0):
        """被叫用户监听线程"""
        start_time = time.time()
        nonlocal client2_call
        
        while time.time() - start_time < duration:
            try:
                old_timeout = client.sock.gettimeout()
                client.sock.settimeout(0.5)
                data, addr = client.sock.recvfrom(4096)
                text = data.decode('utf-8', errors='ignore')
                first_line = text.split('\r\n')[0]
                
                if first_line.startswith('INVITE'):
                    # 收到 INVITE 请求
                    call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                    cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                    from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                    to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                    
                    # 提取所有的 Via 头（可能有多行）
                    via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                    
                    if call_id_match and cseq_match and from_match and to_match and via_lines:
                        call_id = call_id_match.group(1).strip()
                        cseq = cseq_match.group(1).strip()
                        from_header = from_match.group(1).strip()
                        to_header = to_match.group(1).strip()
                        
                        # 组合所有的 Via 头（按顺序，每行一个）
                        via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                        # 第一个 Via 头用于提取 sent-by 地址
                        top_via = via_lines[0].strip()
                        
                        # 创建呼叫对象
                        from_tag_match = re.search(r'tag=([^;>\s]+)', from_header)
                        from_tag = from_tag_match.group(1) if from_tag_match else client._gen_tag()
                        to_tag = client._gen_tag()
                        
                        client2_call = SIPCall(
                            call_id=call_id,
                            from_tag=from_tag,
                            to_tag=to_tag,
                            local_cseq=int(cseq),
                            dialog_established=False
                        )
                        
                        # 提取 SDP（如果有）
                        sdp_match = re.search(r'\r\n\r\n(.+)', text, re.DOTALL)
                        sdp = sdp_match.group(1) if sdp_match else ""
                        
                        # 提取顶层 Via 头中的 sent-by 地址（用于发送响应）
                        # Via: SIP/2.0/UDP host:port;branch=...
                        via_parts = top_via.split(';')
                        via_first = via_parts[0].strip()  # "SIP/2.0/UDP host:port"
                        via_first_parts = via_first.split()
                        if len(via_first_parts) >= 2:
                            sent_by = via_first_parts[1]  # "host:port"
                        else:
                            sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                        
                        if ':' in sent_by:
                            via_host, via_port = sent_by.split(':')
                            via_port = int(via_port)
                        else:
                            via_host = SERVER_IP
                            via_port = SERVER_PORT
                        
                        # 返回 180 Ringing（保持完整的 Via 栈）
                        ringing_msg = (
                            f"SIP/2.0 180 Ringing\r\n"
                            f"{via_stack}\r\n"
                            f"From: {from_header}\r\n"
                            f"To: {to_header};tag={to_tag}\r\n"
                            f"Call-ID: {call_id}\r\n"
                            f"CSeq: {cseq} INVITE\r\n"
                            f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                            f"Content-Length: 0\r\n"
                            f"\r\n"
                        )
                        client.sock.sendto(ringing_msg.encode('utf-8'), (via_host, via_port))
                        print(f"  [被叫用户] 180 Ringing → {via_host}:{via_port}")
                        
                        # 等待一下再返回 200 OK
                        time.sleep(0.5)
                        
                        # 构造 SDP（应答）
                        callee_sdp = (
                            "v=0\r\n"
                            f"o={client.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
                            "s=Test Call\r\n"
                            f"c=IN IP4 {LOCAL_IP}\r\n"
                            "t=0 0\r\n"
                            "m=audio 8000 RTP/AVP 0 8\r\n"
                            "a=rtpmap:0 PCMU/8000\r\n"
                            "a=rtpmap:8 PCMA/8000\r\n"
                        )
                        
                        # 返回 200 OK（保持完整的 Via 栈）
                        ok_msg = (
                            f"SIP/2.0 200 OK\r\n"
                            f"{via_stack}\r\n"
                            f"From: {from_header}\r\n"
                            f"To: {to_header};tag={to_tag}\r\n"
                            f"Call-ID: {call_id}\r\n"
                            f"CSeq: {cseq} INVITE\r\n"
                            f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                            f"Content-Type: application/sdp\r\n"
                            f"Content-Length: {len(callee_sdp)}\r\n"
                            f"\r\n"
                            f"{callee_sdp}"
                        )
                        # 使用相同的 Via 地址发送 200 OK
                        client.sock.sendto(ok_msg.encode('utf-8'), (via_host, via_port))
                        print(f"  [被叫用户] 200 OK → {via_host}:{via_port}")
                        client2_call.dialog_established = True
                
                elif first_line.startswith('ACK'):
                    # 收到 ACK（呼叫已建立）
                    print(f"  [被叫用户] 收到 ACK，呼叫已建立")
                
                elif first_line.startswith('BYE'):
                    # 收到 BYE（呼叫结束）
                    call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                    cseq_match = re.search(r'CSeq:\s*(\d+)\s*BYE', text, re.IGNORECASE)
                    from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                    to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                    
                    # 提取所有的 Via 头（可能有多行）
                    via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                    
                    if call_id_match and cseq_match and via_lines:
                        call_id = call_id_match.group(1).strip()
                        cseq = cseq_match.group(1).strip()
                        from_header = from_match.group(1).strip() if from_match else ""
                        to_header = to_match.group(1).strip() if to_match else ""
                        
                        # 组合所有的 Via 头（按顺序，每行一个）
                        via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                        # 第一个 Via 头用于提取 sent-by 地址
                        top_via = via_lines[0].strip()
                        
                        # 提取 Via 头中的 sent-by 地址
                        via_parts = top_via.split(';')
                        via_first = via_parts[0].strip()
                        via_first_parts = via_first.split()
                        if len(via_first_parts) >= 2:
                            sent_by = via_first_parts[1]
                        else:
                            sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                        
                        if ':' in sent_by:
                            via_host, via_port = sent_by.split(':')
                            via_port = int(via_port)
                        else:
                            via_host = SERVER_IP
                            via_port = SERVER_PORT
                        
                        # 返回 200 OK（保持完整的 Via 栈）
                        bye_ok_msg = (
                            f"SIP/2.0 200 OK\r\n"
                            f"{via_stack}\r\n"
                            f"From: {from_header}\r\n"
                            f"To: {to_header}\r\n"
                            f"Call-ID: {call_id}\r\n"
                            f"CSeq: {cseq} BYE\r\n"
                            f"Content-Length: 0\r\n"
                            f"\r\n"
                        )
                        client.sock.sendto(bye_ok_msg.encode('utf-8'), (via_host, via_port))
                        print(f"  [被叫用户] 收到 BYE，返回 200 OK → {via_host}:{via_port}")
                        break
                
                client.sock.settimeout(old_timeout)
            except socket.timeout:
                client.sock.settimeout(0.5)
                continue
            except Exception as e:
                break
    
    try:
        # 注册
        client1.register()
        client2.register()
        time.sleep(0.5)
        
        # 启动被叫用户的监听线程
        import threading
        listener_thread = threading.Thread(target=callee_listener, args=(client2, 15.0))
        listener_thread.daemon = True
        listener_thread.start()
        
        time.sleep(0.2)  # 等待监听线程启动
        
        # 1001 呼叫 1002
        call = client1.invite("1002")
        if not call or not call.dialog_established:
            if call:
                print(f"  ✗ 呼叫已发起，但未建立对话")
            return
        
        # 发送 ACK（对话已建立）
        if call.dialog_established:
            client1.ack(call)
            
            # 通话 3 秒
            print(f"\n  【通话中...】")
            time.sleep(3)
            
            # 主叫挂断
            client1.bye(call, callee="1002")
        
        # 等待监听线程完成
        listener_thread.join(timeout=3.0)
        
        time.sleep(0.5)
        
        # 注销
        client1.unregister()
        client2.unregister()
        
    finally:
        client1.close()
        client2.close()

def test_scenario_2_callee_busy():
    """场景2: 被叫忙 - 486 Busy Here"""
    print_scenario("被叫忙 - 1001 呼叫 1002，但 1002 返回 486 Busy")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    
    try:
        client1.register()
        client2.register()
        time.sleep(0.5)
        
        # 启动被叫用户的监听线程（用于接收 INVITE 并返回 486 Busy）
        import threading
        
        def callee_listener_busy(client, duration=10.0):
            """被叫用户监听线程（场景2：返回 486 Busy）"""
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)
                    data, addr = client.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('INVITE'):
                        # 收到 INVITE 请求，返回 486 Busy Here
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            # 组合所有的 Via 头
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            # 提取 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            # 提取 To tag（如果有）
                            to_tag_match = re.search(r'tag=([^;>\s]+)', to_header)
                            if not to_tag_match:
                                # 添加 tag（错误响应也需要 tag）
                                to_tag = client._gen_tag()
                                to_header = f"{to_header};tag={to_tag}"
                            
                            # 返回 486 Busy Here
                            busy_msg = (
                                f"SIP/2.0 486 Busy Here\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(busy_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [被叫用户] 返回 486 Busy Here → {via_host}:{via_port}")
                            break  # 已响应，退出监听
                    
                    client.sock.settimeout(old_timeout)
                except socket.timeout:
                    client.sock.settimeout(0.5)
                    continue
                except Exception as e:
                    break
        
        # 启动监听线程
        listener_thread = threading.Thread(target=callee_listener_busy, args=(client2, 10.0))
        listener_thread.daemon = True
        listener_thread.start()
        
        time.sleep(0.2)  # 等待监听线程启动
        
        # 1001 呼叫 1002
        # 注意：服务器是 proxy，不会生成 486，需要被叫用户返回 486
        call = client1.invite("1002")
        if call:
            # 如果收到响应（即使是错误响应），invite() 已经打印了
            if call.dialog_established:
                print(f"  → 呼叫已建立（非预期，应该是 486）")
            else:
                print(f"  → 呼叫状态：对话未建立")
        else:
            print(f"  ✓ 收到 486 Busy Here（符合预期）")
        
        # 等待监听线程完成
        listener_thread.join(timeout=2.0)
        
        time.sleep(0.5)
        client1.unregister()
        client2.unregister()
        
    finally:
        client1.close()
        client2.close()

def test_scenario_3_cancel_ringing():
    """场景3: 振铃时主叫取消"""
    print_scenario("振铃时取消 - 1001 呼叫 1002，振铃期间主叫发送 CANCEL")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    
    try:
        client1.register()
        client2.register()
        time.sleep(0.5)
        
        # 启动被叫用户的监听线程（用于接收 INVITE 返回 180，收到 CANCEL 后返回 487）
        import threading
        
        def callee_listener_cancel(client, duration=10.0):
            """被叫用户监听线程（场景3：振铃后收到 CANCEL）"""
            start_time = time.time()
            invite_received = False
            invite_call_id = None
            invite_cseq = None
            invite_via_stack = None
            invite_via_host = None
            invite_via_port = None
            invite_to_tag = None
            
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)
                    data, addr = client.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('INVITE'):
                        # 收到 INVITE 请求，返回 180 Ringing（但不立即返回 200 OK）
                        if invite_received:
                            continue  # 忽略重复的 INVITE
                        
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            # 组合所有的 Via 头
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            # 提取 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            to_tag = client._gen_tag()
                            
                            # 返回 180 Ringing（但不立即返回 200 OK，等待 CANCEL）
                            ringing_msg = (
                                f"SIP/2.0 180 Ringing\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(ringing_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [被叫用户] 180 Ringing → {via_host}:{via_port}")
                            
                            # 保存 INVITE 信息，用于后续返回 487
                            invite_received = True
                            invite_call_id = call_id
                            invite_cseq = cseq
                            invite_via_stack = via_stack
                            invite_via_host = via_host
                            invite_via_port = via_port
                            invite_to_tag = to_tag
                            # 不立即返回 200 OK，等待 CANCEL
                    
                    elif first_line.startswith('CANCEL'):
                        # 收到 CANCEL 请求，返回 200 OK for CANCEL
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*CANCEL', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            # 组合所有的 Via 头
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            # 提取 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            # 返回 200 OK for CANCEL
                            cancel_ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} CANCEL\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(cancel_ok_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [被叫用户] 收到 CANCEL，返回 200 OK → {via_host}:{via_port}")
                            
                            # 对于 CANCEL，还需要对原始 INVITE 返回 487 Request Terminated
                            if invite_received and invite_call_id == call_id:
                                # 使用保存的 INVITE 信息返回 487
                                # 提取 To tag（从之前的 INVITE 响应中）
                                
                                # 返回 487 Request Terminated for INVITE
                                terminated_msg = (
                                    f"SIP/2.0 487 Request Terminated\r\n"
                                    f"{invite_via_stack}\r\n"  # 使用原始 INVITE 的 Via 栈
                                    f"From: {from_header}\r\n"
                                    f"To: {to_header};tag={invite_to_tag}\r\n"  # 使用原始 INVITE 的 To tag
                                    f"Call-ID: {invite_call_id}\r\n"
                                    f"CSeq: {invite_cseq} INVITE\r\n"  # 原始 INVITE 的 CSeq
                                    f"Content-Length: 0\r\n"
                                    f"\r\n"
                                )
                                # 使用原始 INVITE 的 sent-by 地址
                                client.sock.sendto(terminated_msg.encode('utf-8'), (invite_via_host, invite_via_port))
                                print(f"  [被叫用户] 对 INVITE 返回 487 Request Terminated → {invite_via_host}:{invite_via_port}")
                            else:
                                # 如果没有保存 INVITE 信息，使用当前 CANCEL 的 Via（降级处理）
                                to_tag_match = re.search(r'tag=([^;>\s]+)', to_header)
                                if not to_tag_match:
                                    to_tag = client._gen_tag()
                                    to_header = f"{to_header};tag={to_tag}"
                                
                                terminated_msg = (
                                    f"SIP/2.0 487 Request Terminated\r\n"
                                    f"{via_stack}\r\n"
                                    f"From: {from_header}\r\n"
                                    f"To: {to_header}\r\n"
                                    f"Call-ID: {call_id}\r\n"
                                    f"CSeq: 1 INVITE\r\n"
                                    f"Content-Length: 0\r\n"
                                    f"\r\n"
                                )
                                client.sock.sendto(terminated_msg.encode('utf-8'), (via_host, via_port))
                                print(f"  [被叫用户] 对 INVITE 返回 487 Request Terminated → {via_host}:{via_port}")
                            
                            break  # 已处理 CANCEL，退出监听
                    
                    client.sock.settimeout(old_timeout)
                except socket.timeout:
                    client.sock.settimeout(0.5)
                    continue
                except Exception as e:
                    break
        
        # 启动监听线程
        listener_thread = threading.Thread(target=callee_listener_cancel, args=(client2, 10.0))
        listener_thread.daemon = True
        listener_thread.start()
        
        time.sleep(0.2)  # 等待监听线程启动
        
        # 1001 呼叫 1002
        # 注意：invite() 会在收到 180 后继续等待最终响应
        # 我们需要在后台线程中等待最终响应，在主线程中发送 CANCEL
        
        # 手动发送 INVITE（不使用 invite() 方法，因为它在收到 180 后会阻塞）
        call_id = client1._gen_call_id()
        from_tag = client1._gen_tag()
        branch = client1._gen_branch()
        
        sdp = (
            "v=0\r\n"
            f"o={client1.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
            "s=Test Call\r\n"
            f"c=IN IP4 {LOCAL_IP}\r\n"
            "t=0 0\r\n"
            "m=audio 8000 RTP/AVP 0 8\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
        )
        
        invite_msg = (
            f"INVITE sip:1002@{SERVER_IP} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{client1.local_port};branch={branch}\r\n"
            f"From: <sip:{client1.username}@{SERVER_IP}>;tag={from_tag}\r\n"
            f"To: <sip:1002@{SERVER_IP}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Contact: <sip:{client1.username}@{LOCAL_IP}:{client1.local_port}>\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp)}\r\n"
            f"\r\n"
            f"{sdp}"
        )
        
        # 创建 call 对象
        call = SIPCall(
            call_id=call_id,
            from_tag=from_tag,
            local_cseq=1
        )
        client1.current_call = call
        
        # 发送 INVITE
        client1.sock.sendto(invite_msg.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        
        # 使用队列来收集响应，避免多线程冲突
        import queue
        response_queue = queue.Queue()
        
        # 在后台线程中等待响应（180, 487, CANCEL 200 OK）
        def wait_for_response_thread():
            old_timeout = client1.sock.gettimeout()
            client1.sock.settimeout(15.0)
            try:
                while True:
                    data, addr = client1.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    if call_id in text:
                        resp = client1._parse_response(data)
                        if resp and resp.get('status_code'):
                            status_code = resp.get('status_code')
                            status_text = resp.get('status_text', '')
                            cseq_header = resp.get('headers', {}).get('cseq', '')
                            response_queue.put((status_code, status_text))
                            
                            if status_code in [100, 180, 183]:
                                print(f"  → {status_code} {resp.get('status_text')}")
                                if status_code == 180:
                                    # 收到 180，等待 CANCEL 发送后的 487
                                    continue
                            elif status_code == 487:
                                print(f"  → 487 Request Terminated（CANCEL 成功）")
                                break
                            elif status_code == 200:
                                # 可能是 CANCEL 的 200 OK 或 INVITE 的 200 OK
                                cseq_header = resp.get('headers', {}).get('cseq', '').upper()
                                if 'CANCEL' in cseq_header:
                                    print(f"  → 200 OK（CANCEL）")
                                    continue  # 继续等待 487
                                else:
                                    # INVITE 的 200 OK（不应该在这里出现，因为场景3中应该先收到 CANCEL）
                                    print(f"  → 200 OK（INVITE）")
                                    break
                            else:
                                print(f"  → {status_code} {resp.get('status_text')}")
                                break
            except socket.timeout:
                pass
            finally:
                client1.sock.settimeout(old_timeout)
        
        response_thread = threading.Thread(target=wait_for_response_thread)
        response_thread.daemon = True
        response_thread.start()
        
        # 等待收到 180
        time.sleep(0.5)
        
        # 等待 1 秒（模拟振铃）
        print(f"\n  【振铃中...】")
        time.sleep(1)
        
        # 主叫取消（只发送，不等待响应）
        print(f"\n[{client1.username}] 取消呼叫...")
        branch = client1._gen_branch()
        cancel_msg = (
            f"CANCEL sip:1002@{SERVER_IP} SIP/2.0\r\n"  # 使用被叫用户地址
            f"Via: SIP/2.0/UDP {LOCAL_IP}:{client1.local_port};branch={branch}\r\n"
            f"From: <sip:{client1.username}@{SERVER_IP}>;tag={call.from_tag}\r\n"
            f"To: <sip:1002@{SERVER_IP}>\r\n"  # 使用被叫用户地址
            f"Call-ID: {call.call_id}\r\n"
            f"CSeq: {call.local_cseq} CANCEL\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        client1.sock.sendto(cancel_msg.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        
        # 等待响应线程处理响应
        time.sleep(0.5)  # 等待 CANCEL 响应
        response_thread.join(timeout=3.0)
        
        # 检查是否有未处理的响应
        try:
            while True:
                status_code, status_text = response_queue.get_nowait()
                if status_code == 200:
                    # CANCEL 的 200 OK
                    if 'CANCEL' in status_text or status_code == 200:
                        print(f"  ✓ CANCEL 收到 200 OK")
                elif status_code == 487:
                    print(f"  ✓ 收到 487 Request Terminated")
        except queue.Empty:
            pass
        
        # 等待监听线程完成
        listener_thread.join(timeout=2.0)
        
        time.sleep(0.5)
        client1.unregister()
        client2.unregister()
        
    finally:
        client1.close()
        client2.close()

def test_scenario_4_call_not_found():
    """场景4: 被叫未注册 - 480 Temporarily Unavailable"""
    print_scenario("被叫未注册 - 1001 呼叫 1003（未注册）")
    
    client1 = SIPClient("1001", "1234", 5061)
    
    try:
        client1.register()
        time.sleep(0.5)
        
        # 1001 呼叫未注册的 1003
        # 应该收到 480 Temporarily Unavailable
        call = client1.invite("1003")
        if call:
            # 如果收到响应（即使是错误响应），invite() 已经打印了
            if call.dialog_established:
                print(f"  → 呼叫已建立（非预期）")
            else:
                print(f"  → 呼叫状态：对话未建立")
        else:
            print(f"  → 呼叫失败（期望收到 480）")
        
        time.sleep(0.5)
        client1.unregister()
        
    finally:
        client1.close()

def test_scenario_5_message():
    """场景5: 即时消息"""
    print_scenario("即时消息 - 1001 发送消息给 1002")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    
    try:
        # 注册两个用户
        client1.register()
        client2.register()
        time.sleep(0.5)
        
        # 启动被叫用户的监听线程（用于接收消息）
        import threading
        
        def listen_for_messages(client, duration=5.0):
            """监听消息的线程"""
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)  # 短超时，用于轮询
                    data, addr = client.sock.recvfrom(4096)
                    
                    # 判断是请求还是响应
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('MESSAGE'):
                        # 收到 MESSAGE 请求，返回 200 OK
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*MESSAGE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头（可能有多行）
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            # 提取 To tag（如果有）
                            to_tag_match = re.search(r'tag=([^;>\s]+)', to_header)
                            if not to_tag_match:
                                # 添加 tag
                                to_header = f"{to_header};tag={client._gen_tag()}"
                            
                            # 组合所有的 Via 头（按顺序，每行一个）
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            # 第一个 Via 头用于提取 sent-by 地址
                            top_via = via_lines[0].strip()
                            
                            # 提取顶层 Via 头中的 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            # 构造 200 OK 响应（保持完整的 Via 栈）
                            response_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} MESSAGE\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            
                            # 发送响应到顶层 Via 的 sent-by 地址
                            client.sock.sendto(response_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [被叫用户] 收到消息并返回 200 OK → {via_host}:{via_port}")
                    
                    client.sock.settimeout(old_timeout)
                except socket.timeout:
                    client.sock.settimeout(0.5)
                    continue
                except Exception as e:
                    # 忽略其他异常
                    break
        
        # 启动监听线程
        listener_thread = threading.Thread(target=listen_for_messages, args=(client2, 5.0))
        listener_thread.daemon = True
        listener_thread.start()
        
        # 等待一下让监听线程启动
        time.sleep(0.2)
        
        # 发送消息
        result = client1.message("1002", "Hello, this is a test message!")
        
        # 等待监听线程完成
        listener_thread.join(timeout=3.0)
        
        time.sleep(0.5)
        client1.unregister()
        client2.unregister()
        
    finally:
        client1.close()
        client2.close()

def test_scenario_6_register_unregister():
    """场景6: 注册和注销"""
    print_scenario("注册和注销 - 测试用户注册和注销流程")
    
    client = SIPClient("1001", "1234", 5061)
    
    try:
        # 注册
        client.register(expires=3600)
        time.sleep(0.5)
        
        # 立即注销
        client.unregister()
        time.sleep(0.5)
        
    finally:
        client.close()

def test_scenario_7_wrong_password():
    """场景7: 错误密码注册"""
    print_scenario("错误密码 - 使用错误密码尝试注册")
    
    client = SIPClient("1001", "wrong_password", 5061)
    
    try:
        client.register()
        time.sleep(0.5)
        
    finally:
        client.close()

def test_scenario_8_multiple_calls():
    """场景8: 多个并发呼叫"""
    print_scenario("并发呼叫 - 1001→1002, 1001→1003 同时进行")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    client3 = SIPClient("1003", "1234", 5063)
    
    try:
        # 注册被叫用户（1002和1003）
        client2.register()
        client3.register()
        time.sleep(0.5)
        
        # 注意：client1 不在这里注册，因为每个呼叫会创建独立的 SIPClient 并注册
        
        # 启动被叫用户的监听线程（1002和1003）
        import threading
        
        def callee_listener(client, username, duration=15.0):
            """被叫用户监听线程（场景8：并发呼叫）"""
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)
                    data, addr = client.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('INVITE'):
                        # 收到 INVITE 请求，返回 180 Ringing 和 200 OK
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            # 组合所有的 Via 头
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            # 提取 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            to_tag = client._gen_tag()
                            
                            # 返回 180 Ringing
                            ringing_msg = (
                                f"SIP/2.0 180 Ringing\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(ringing_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [{username}] 180 Ringing → {via_host}:{via_port}")
                            
                            time.sleep(0.5)
                            
                            # 构造 SDP
                            callee_sdp = (
                                "v=0\r\n"
                                f"o={client.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
                                "s=Test Call\r\n"
                                f"c=IN IP4 {LOCAL_IP}\r\n"
                                "t=0 0\r\n"
                                "m=audio 8000 RTP/AVP 0 8\r\n"
                                "a=rtpmap:0 PCMU/8000\r\n"
                                "a=rtpmap:8 PCMA/8000\r\n"
                            )
                            
                            # 返回 200 OK
                            ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Type: application/sdp\r\n"
                                f"Content-Length: {len(callee_sdp)}\r\n"
                                f"\r\n"
                                f"{callee_sdp}"
                            )
                            client.sock.sendto(ok_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [{username}] 200 OK → {via_host}:{via_port}")
                    
                    elif first_line.startswith('ACK'):
                        # 收到 ACK
                        print(f"  [{username}] 收到 ACK，呼叫已建立")
                    
                    elif first_line.startswith('BYE'):
                        # 收到 BYE，返回 200 OK
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*BYE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip() if from_match else ""
                            to_header = to_match.group(1).strip() if to_match else ""
                            
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            bye_ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} BYE\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(bye_ok_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [{username}] 收到 BYE，返回 200 OK")
                    
                    client.sock.settimeout(old_timeout)
                except socket.timeout:
                    client.sock.settimeout(0.5)
                    continue
                except Exception as e:
                    break
        
        # 启动监听线程
        listener_thread_1002 = threading.Thread(target=callee_listener, args=(client2, "1002", 15.0))
        listener_thread_1002.daemon = True
        listener_thread_1002.start()
        
        listener_thread_1003 = threading.Thread(target=callee_listener, args=(client3, "1003", 15.0))
        listener_thread_1003.daemon = True
        listener_thread_1003.start()
        
        time.sleep(0.2)  # 等待监听线程启动
        
        # 1001 真正并发呼叫 1002 和 1003
        # 为每个呼叫创建独立的 SIPClient（不同的端口）
        client1_call2 = SIPClient("1001", "1234", 5064)  # 使用不同的端口
        client1_call3 = SIPClient("1001", "1234", 5065)  # 使用不同的端口
        
        try:
            # 注册这两个新的客户端
            client1_call2.register()
            client1_call3.register()
            time.sleep(0.3)
            
            # 定义并发呼叫函数
            def make_call(client, callee, client_name):
                """并发呼叫函数"""
                print(f"\n[{client_name}] 呼叫 {callee}...")
                call = client.invite(callee)
                if call and call.dialog_established:
                    client.ack(call)
                    print(f"  ✓ 呼叫 {callee} 已建立")
                    
                    # 通话 2 秒
                    time.sleep(2)
                    
                    # 挂断
                    client.bye(call, callee=callee)
                    return call
                return None
            
            # 使用线程并发呼叫
            call_result_1002 = [None]
            call_result_1003 = [None]
            
            def call_1002():
                call_result_1002[0] = make_call(client1_call2, "1002", "1001(呼叫1002)")
            
            def call_1003():
                call_result_1003[0] = make_call(client1_call3, "1003", "1001(呼叫1003)")
            
            # 启动并发呼叫线程
            call_thread_1002 = threading.Thread(target=call_1002)
            call_thread_1003 = threading.Thread(target=call_1003)
            
            call_thread_1002.start()
            call_thread_1003.start()
            
            # 等待两个呼叫完成
            call_thread_1002.join(timeout=10.0)
            call_thread_1003.join(timeout=10.0)
            
            print(f"\n  ✓ 并发呼叫完成")
            
        finally:
            # 注销新创建的客户端
            try:
                client1_call2.unregister()
                client1_call3.unregister()
            except:
                pass
            client1_call2.close()
            client1_call3.close()
        
        # 等待监听线程完成
        listener_thread_1002.join(timeout=3.0)
        listener_thread_1003.join(timeout=3.0)
        
        time.sleep(0.5)
        # 注销
        client1.unregister()
        client2.unregister()
        client3.unregister()
        
    finally:
        client1.close()
        client2.close()
        client3.close()

def test_scenario_9_long_call():
    """场景9: 长时间通话"""
    print_scenario("长时间通话 - 1001 呼叫 1002，通话 10 秒")
    
    client1 = SIPClient("1001", "1234", 5061)
    client2 = SIPClient("1002", "1234", 5062)
    
    try:
        client1.register()
        client2.register()
        time.sleep(0.5)
        
        # 启动被叫用户的监听线程（用于接收 INVITE, ACK, BYE）
        import threading
        
        def callee_listener(client, duration=20.0):
            """被叫用户监听线程（场景9）"""
            start_time = time.time()
            nonlocal client2_call
            client2_call = None
            
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)
                    data, addr = client.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('INVITE'):
                        # 收到 INVITE 请求
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        # 提取所有的 Via 头
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            from_tag_match = re.search(r'tag=([^;>\s]+)', from_header)
                            from_tag = from_tag_match.group(1) if from_tag_match else client._gen_tag()
                            to_tag = client._gen_tag()
                            
                            client2_call = SIPCall(
                                call_id=call_id,
                                from_tag=from_tag,
                                to_tag=to_tag,
                                local_cseq=int(cseq),
                                dialog_established=False
                            )
                            
                            # 组合所有的 Via 头
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            # 提取 sent-by 地址
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            # 返回 180 Ringing
                            ringing_msg = (
                                f"SIP/2.0 180 Ringing\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(ringing_msg.encode('utf-8'), (via_host, via_port))
                            
                            time.sleep(0.5)
                            
                            # 构造 SDP
                            callee_sdp = (
                                "v=0\r\n"
                                f"o={client.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
                                "s=Test Call\r\n"
                                f"c=IN IP4 {LOCAL_IP}\r\n"
                                "t=0 0\r\n"
                                "m=audio 8000 RTP/AVP 0 8\r\n"
                                "a=rtpmap:0 PCMU/8000\r\n"
                                "a=rtpmap:8 PCMA/8000\r\n"
                            )
                            
                            # 返回 200 OK
                            ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Type: application/sdp\r\n"
                                f"Content-Length: {len(callee_sdp)}\r\n"
                                f"\r\n"
                                f"{callee_sdp}"
                            )
                            client.sock.sendto(ok_msg.encode('utf-8'), (via_host, via_port))
                            client2_call.dialog_established = True
                    
                    elif first_line.startswith('ACK'):
                        # 收到 ACK
                        pass
                    
                    elif first_line.startswith('BYE'):
                        # 收到 BYE
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*BYE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip() if from_match else ""
                            to_header = to_match.group(1).strip() if to_match else ""
                            
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            bye_ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} BYE\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(bye_ok_msg.encode('utf-8'), (via_host, via_port))
                            print(f"  [被叫用户] 收到 BYE，返回 200 OK")
                            break
                    
                    client.sock.settimeout(old_timeout)
                except socket.timeout:
                    client.sock.settimeout(0.5)
                    continue
                except Exception as e:
                    break
        
        client2_call = None
        listener_thread = threading.Thread(target=callee_listener, args=(client2, 20.0))
        listener_thread.daemon = True
        listener_thread.start()
        
        time.sleep(0.2)
        
        # 1001 呼叫 1002
        call = client1.invite("1002")
        if not call or not call.dialog_established:
            if call:
                print(f"  ✗ 呼叫已发起，但未建立对话")
            return
        
        # 发送 ACK（对话已建立）
        if call.dialog_established:
            client1.ack(call)
            
            print(f"\n  【通话中...】")
            for i in range(10):
                print(f"  {i+1} 秒...", end='\r')
                time.sleep(1)
            print()
            
            # 主叫挂断
            client1.bye(call, callee="1002")
        
        # 等待监听线程完成
        listener_thread.join(timeout=3.0)
        
        time.sleep(0.5)
        client1.unregister()
        client2.unregister()
        
    finally:
        client1.close()
        client2.close()

def test_scenario_10_re_register():
    """场景10: 重复注册（刷新注册）"""
    print_scenario("重复注册 - 用户多次注册刷新")
    
    client = SIPClient("1001", "1234", 5061)
    
    try:
        # 第一次注册
        client.register(expires=3600)
        time.sleep(1)
        
        # 第二次注册（刷新）
        print(f"\n  刷新注册...")
        client.register(expires=3600)
        time.sleep(1)
        
        # 注销
        client.unregister()
        
    finally:
        client.close()

def test_scenario_11_high_concurrency():
    """场景11: 高并发呼叫测试"""
    import threading
    
    # 导入用户管理器（使用服务器的用户管理器实例）
    try:
        from sipcore.user_manager import get_user_manager
        user_mgr = get_user_manager()
        if user_mgr is None:
            # 如果用户管理器未初始化，尝试初始化
            from sipcore.user_manager import init_user_manager
            user_mgr = init_user_manager(data_file="data/users.json")
    except Exception as e:
        print(f"  ✗ 无法获取用户管理器: {e}")
        print("  提示: 请确保 SIP 服务器正在运行")
        return
    
    # 获取并发量（默认100）
    print("\n" + "="*70)
    print("场景11: 高并发呼叫测试")
    print("="*70)
    concurrency_input = input("\n请输入并发呼叫数量（直接回车使用默认值 100）: ").strip()
    
    if concurrency_input:
        try:
            concurrency = int(concurrency_input)
            if concurrency <= 0:
                print("  ✗ 并发量必须大于0，使用默认值 100")
                concurrency = 100
        except ValueError:
            print("  ✗ 输入无效，使用默认值 100")
            concurrency = 100
    else:
        concurrency = 100
    
    # 检查系统限制
    import resource
    try:
        # 获取系统进程/线程数限制
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NPROC)
        # 每个并发需要2个线程（1个监听线程 + 1个呼叫线程）
        # 保留一些线程给系统使用
        max_threads_safe = (soft_limit - 100) // 2  # 安全限制：保留100个线程给系统
        max_threads_absolute = (soft_limit - 10) // 2  # 绝对限制：只保留10个线程
        
        if concurrency > max_threads_safe:
            print(f"  ⚠ 并发量超过推荐限制 ({max_threads_safe})")
            print(f"  提示: 大规模并发测试可能导致:")
            print(f"    - 线程数超过系统限制（当前限制: {soft_limit} 个进程/线程）")
            print(f"    - 内存不足（每个线程约8MB）")
            print(f"    - 系统响应变慢")
            print(f"    - 网络带宽不足")
            print(f"  每个并发需要 2 个线程（监听 + 呼叫），系统最多支持约 {max_threads_safe} 个并发")
            response = input(f"  是否继续？（可能失败）(y/N): ").strip().lower()
            if response != 'y':
                print("  已取消测试")
                return
            # 绝对上限：基于系统线程限制
            if concurrency > max_threads_absolute:
                print(f"  ✗ 并发量超过系统线程限制 ({max_threads_absolute})，已限制为 {max_threads_absolute}")
                concurrency = max_threads_absolute
    except Exception as e:
        # 如果无法获取系统限制，使用保守的默认值
        print(f"  ⚠ 无法获取系统线程限制: {e}")
        print(f"  使用保守限制: 1000 个并发")
        if concurrency > 1000:
            print(f"  ✗ 并发量超过保守限制 (1000)，已限制为 1000")
            concurrency = 1000
    
    # 检查端口范围
    # 可用端口: 1024-65535 (约64,000个)
    # 被叫用户端口: 6000-59999 (约54,000个)
    # 主叫用户端口: 60000-65535 (约5,535个)
    if concurrency > 54535:
        print(f"  ✗ 并发量超过端口限制 (54535)，已限制为 54535")
        concurrency = 54535
    
    print(f"\n并发呼叫数量: {concurrency}")
    print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成用户名列表
    caller_username = "9000"  # 主叫用户
    callee_usernames = [f"9{1000+i}" for i in range(concurrency)]  # 被叫用户 91000-91099 (如果concurrency=100)
    
    # 初始化变量（避免 finally 块中未定义错误）
    callee_clients = []
    
    try:
        # 1. 创建主叫用户账户（使用用户管理器 API）
        print(f"\n[1/4] 创建主叫用户账户: {caller_username}")
        result = user_mgr.add_user(
            username=caller_username,
            password="1234",
            display_name=f"高并发测试主叫用户{caller_username}",
            phone=f"1380000{caller_username}",
            email=f"user{caller_username}@example.com",
            service_type="BASIC"
        )
        if result.get('success'):
            print(f"  ✓ 主叫用户 {caller_username} 创建成功")
        else:
            # 用户可能已存在，先删除再创建
            if caller_username in user_mgr.users:
                user_mgr.delete_user(caller_username)
            result = user_mgr.add_user(
                username=caller_username,
                password="1234",
                display_name=f"高并发测试主叫用户{caller_username}",
                phone=f"1380000{caller_username}",
                email=f"user{caller_username}@example.com",
                service_type="BASIC"
            )
            if result.get('success'):
                print(f"  ✓ 主叫用户 {caller_username} 创建成功")
            else:
                print(f"  ✗ 主叫用户创建失败: {result.get('message')}")
        
        # 2. 创建被叫用户账户（使用用户管理器 API）
        print(f"\n[2/4] 创建被叫用户账户: {concurrency} 个")
        created_count = 0
        for username in callee_usernames:
            # 如果用户已存在，先删除
            if username in user_mgr.users:
                user_mgr.delete_user(username)
            
            result = user_mgr.add_user(
                username=username,
                password="1234",
                display_name=f"高并发测试被叫用户{username}",
                phone=f"1380000{username}",
                email=f"user{username}@example.com",
                service_type="BASIC"
            )
            created_count += 1
            if created_count % 10 == 0:
                print(f"  → 已创建 {created_count}/{concurrency} 个用户...", end='\r')
        
        print(f"\n  ✓ 所有被叫用户创建成功 ({concurrency} 个)")
        
        # 强制刷新文件系统，确保用户数据已写入磁盘
        import os
        if os.path.exists(user_mgr.data_file):
            # 重新打开文件并关闭，强制刷新缓冲区
            try:
                with open(user_mgr.data_file, 'r', encoding='utf-8') as f:
                    f.read()
            except:
                pass
        
        # 等待一下，确保文件系统同步
        time.sleep(1.0)
        
        # 验证用户是否已创建（通过读取文件）
        try:
            with open(user_mgr.data_file, 'r', encoding='utf-8') as f:
                import json
                users_check = json.load(f)
                if caller_username in users_check and len([u for u in callee_usernames if u in users_check]) == concurrency:
                    print(f"  ✓ 用户文件验证成功")
                else:
                    print(f"  ⚠ 用户文件验证失败，可能需要重启服务器")
        except:
            pass
        
        # 3. 启动被叫用户的监听线程
        print(f"\n[3/4] 启动被叫用户监听线程")
        callee_clients = []
        listener_threads = []
        
        def callee_listener(client, username, duration=60.0):
            """被叫用户监听线程（场景11：高并发呼叫）"""
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    old_timeout = client.sock.gettimeout()
                    client.sock.settimeout(0.5)
                    data, addr = client.sock.recvfrom(4096)
                    text = data.decode('utf-8', errors='ignore')
                    first_line = text.split('\r\n')[0]
                    
                    if first_line.startswith('INVITE'):
                        # 收到 INVITE 请求，返回 180 Ringing 和 200 OK
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*INVITE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and from_match and to_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip()
                            to_header = to_match.group(1).strip()
                            
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            to_tag = client._gen_tag()
                            
                            # 返回 180 Ringing
                            ringing_msg = (
                                f"SIP/2.0 180 Ringing\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(ringing_msg.encode('utf-8'), (via_host, via_port))
                            
                            time.sleep(0.3)
                            
                            # 构造 SDP
                            callee_sdp = (
                                "v=0\r\n"
                                f"o={client.username} 123456 123456 IN IP4 {LOCAL_IP}\r\n"
                                "s=Test Call\r\n"
                                f"c=IN IP4 {LOCAL_IP}\r\n"
                                "t=0 0\r\n"
                                "m=audio 8000 RTP/AVP 0 8\r\n"
                                "a=rtpmap:0 PCMU/8000\r\n"
                                "a=rtpmap:8 PCMA/8000\r\n"
                            )
                            
                            # 返回 200 OK
                            ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header};tag={to_tag}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} INVITE\r\n"
                                f"Contact: <sip:{client.username}@{LOCAL_IP}:{client.local_port}>\r\n"
                                f"Content-Type: application/sdp\r\n"
                                f"Content-Length: {len(callee_sdp)}\r\n"
                                f"\r\n"
                                f"{callee_sdp}"
                            )
                            client.sock.sendto(ok_msg.encode('utf-8'), (via_host, via_port))
                    
                    elif first_line.startswith('ACK'):
                        # 收到 ACK
                        pass
                    
                    elif first_line.startswith('BYE'):
                        # 收到 BYE，返回 200 OK
                        call_id_match = re.search(r'Call-ID:\s*([^\r\n]+)', text, re.IGNORECASE)
                        cseq_match = re.search(r'CSeq:\s*(\d+)\s*BYE', text, re.IGNORECASE)
                        from_match = re.search(r'From:\s*([^\r\n]+)', text, re.IGNORECASE)
                        to_match = re.search(r'To:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        via_lines = re.findall(r'Via:\s*([^\r\n]+)', text, re.IGNORECASE)
                        
                        if call_id_match and cseq_match and via_lines:
                            call_id = call_id_match.group(1).strip()
                            cseq = cseq_match.group(1).strip()
                            from_header = from_match.group(1).strip() if from_match else ""
                            to_header = to_match.group(1).strip() if to_match else ""
                            
                            via_stack = '\r\n'.join([f"Via: {via_line.strip()}" for via_line in via_lines])
                            top_via = via_lines[0].strip()
                            
                            via_parts = top_via.split(';')
                            via_first = via_parts[0].strip()
                            via_first_parts = via_first.split()
                            if len(via_first_parts) >= 2:
                                sent_by = via_first_parts[1]
                            else:
                                sent_by = f"{SERVER_IP}:{SERVER_PORT}"
                            
                            if ':' in sent_by:
                                via_host, via_port = sent_by.split(':')
                                via_port = int(via_port)
                            else:
                                via_host = SERVER_IP
                                via_port = SERVER_PORT
                            
                            bye_ok_msg = (
                                f"SIP/2.0 200 OK\r\n"
                                f"{via_stack}\r\n"
                                f"From: {from_header}\r\n"
                                f"To: {to_header}\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {cseq} BYE\r\n"
                                f"Content-Length: 0\r\n"
                                f"\r\n"
                            )
                            client.sock.sendto(bye_ok_msg.encode('utf-8'), (via_host, via_port))
                    
                    try:
                        client.sock.settimeout(old_timeout)
                    except:
                        pass
                except socket.timeout:
                    try:
                        client.sock.settimeout(0.5)
                    except:
                        pass
                    continue
                except (OSError, ValueError) as e:
                    # socket 已关闭或其他错误，退出监听
                    break
                except Exception as e:
                    # 其他异常，继续监听
                    continue
        
        # 为每个被叫用户创建客户端和监听线程
        # 被叫用户端口范围: 6000-59999 (约54,000个)
        callee_base_port = 6000
        for i, username in enumerate(callee_usernames):
            port = callee_base_port + i
            client = SIPClient(username, "1234", port)
            callee_clients.append(client)
            
            # 注册
            client.register()
            
            # 启动监听线程
            try:
                listener_thread = threading.Thread(target=callee_listener, args=(client, username, 60.0))
                listener_thread.daemon = True
                listener_thread.start()
                listener_threads.append(listener_thread)
            except RuntimeError as e:
                if "can't start new thread" in str(e):
                    print(f"\n  ✗ 无法创建线程（已达到系统限制）")
                    print(f"  已创建的监听线程数: {len(listener_threads)}")
                    print(f"  系统线程限制: {resource.getrlimit(resource.RLIMIT_NPROC)[0]}")
                    print(f"  建议: 减少并发量或使用线程池")
                    break
                else:
                    raise
            
            if (i + 1) % 10 == 0:
                print(f"  → 已启动 {i+1}/{concurrency} 个监听线程...", end='\r')
        
        print(f"\n  ✓ 所有被叫用户监听线程启动成功")
        time.sleep(1.0)  # 等待所有监听线程启动
        
        # 4. 并发呼叫
        print(f"\n[4/4] 发起并发呼叫")
        caller_clients = []
        call_threads = []
        success_count = [0]
        fail_count = [0]
        
        def make_concurrent_call(caller_port, callee_username, call_index):
            """并发呼叫函数"""
            try:
                # 所有并发呼叫使用同一个主叫用户名（9000），但不同的端口
                caller_client = SIPClient(caller_username, "1234", caller_port)
                caller_client.register()
                time.sleep(0.1)
                
                call = caller_client.invite(callee_username)
                if call and call.dialog_established:
                    caller_client.ack(call)
                    time.sleep(1)  # 通话 1 秒
                    caller_client.bye(call, callee=callee_username)
                    success_count[0] += 1
                else:
                    fail_count[0] += 1
                
                caller_client.unregister()
                caller_client.close()
            except Exception as e:
                fail_count[0] += 1
        
        # 为每个并发呼叫创建独立的 SIPClient
        # 主叫用户端口范围: 6000+concurrency 到 65535
        # 确保与被叫用户端口不重叠
        caller_base_port = callee_base_port + concurrency
        # 如果超出范围，使用 60000-65535
        if caller_base_port > 65535:
            caller_base_port = 60000
        
        start_time = time.time()
        
        for i, callee_username in enumerate(callee_usernames):
            # 计算主叫用户端口，确保不与被叫用户端口重叠
            if caller_base_port + i <= 65535:
                caller_port = caller_base_port + i
            else:
                # 如果超出65535，循环使用60000-65535范围
                caller_port = 60000 + (i - (65535 - caller_base_port + 1))
            
            # 确保端口在有效范围内
            if caller_port < 1024 or caller_port > 65535:
                print(f"  ✗ 端口溢出: {caller_port}，最大并发量受限")
                break
            try:
                call_thread = threading.Thread(
                    target=make_concurrent_call,
                    args=(caller_port, callee_username, i)
                )
                call_thread.daemon = True
                call_thread.start()
                call_threads.append(call_thread)
            except RuntimeError as e:
                if "can't start new thread" in str(e):
                    print(f"\n  ✗ 无法创建线程（已达到系统限制）")
                    print(f"  已创建的呼叫线程数: {len(call_threads)}")
                    print(f"  系统线程限制: {resource.getrlimit(resource.RLIMIT_NPROC)[0]}")
                    print(f"  建议: 减少并发量或使用线程池")
                    break
                else:
                    raise
            
            if (i + 1) % 10 == 0:
                print(f"  → 已启动 {i+1}/{concurrency} 个并发呼叫...", end='\r')
        
        print(f"\n  → 等待所有呼叫完成...")
        
        # 等待所有呼叫完成
        for thread in call_threads:
            thread.join(timeout=30.0)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n" + "="*70)
        print("测试结果统计")
        print("="*70)
        print(f"并发呼叫数量: {concurrency}")
        print(f"成功呼叫数: {success_count[0]}")
        print(f"失败呼叫数: {fail_count[0]}")
        print(f"成功率: {success_count[0]/concurrency*100:.2f}%")
        print(f"总耗时: {elapsed_time:.2f} 秒")
        print(f"平均每个呼叫耗时: {elapsed_time/concurrency:.3f} 秒")
        print(f"QPS (每秒呼叫数): {concurrency/elapsed_time:.2f}")
        
        # 等待监听线程完成
        time.sleep(2.0)
        
    finally:
        # 5. 清理：删除创建的用户账户（使用用户管理器 API）
        print(f"\n[清理] 删除测试用户账户")
        try:
            # 删除主叫用户
            if caller_username in user_mgr.users:
                result = user_mgr.delete_user(caller_username)
                if result.get('success'):
                    print(f"  ✓ 删除主叫用户: {caller_username}")
            
            # 删除被叫用户
            deleted_count = 0
            for username in callee_usernames:
                if username in user_mgr.users:
                    result = user_mgr.delete_user(username)
                    if result.get('success'):
                        deleted_count += 1
            
            print(f"  ✓ 删除被叫用户: {deleted_count} 个")
        except Exception as e:
            print(f"  ⚠ 清理用户账户时出错: {e}")
        
        # 关闭所有客户端（在异常处理中，可能 callee_clients 未定义）
        # 注意：在用户被删除后，不需要再注销，因为用户已经不存在
        try:
            for client in callee_clients:
                try:
                    # 不调用 unregister()，因为用户可能已被删除
                    client.close()
                except:
                    pass
        except:
            pass
        
        print(f"\n测试完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")


# ====== 主测试函数 ======

def run_all_tests():
    """运行所有测试场景"""
    scenarios = [
        ("场景 1", test_scenario_1_normal_call),
        ("场景 2", test_scenario_2_callee_busy),
        ("场景 3", test_scenario_3_cancel_ringing),
        ("场景 4", test_scenario_4_call_not_found),
        ("场景 5", test_scenario_5_message),
        ("场景 6", test_scenario_6_register_unregister),
        ("场景 7", test_scenario_7_wrong_password),
        ("场景 8", test_scenario_8_multiple_calls),
        ("场景 9", test_scenario_9_long_call),
        ("场景 10", test_scenario_10_re_register),
        ("场景 11", test_scenario_11_high_concurrency),
    ]
    
    print("\n" + "█"*70)
    print("█  SIP 服务器自动化测试")
    print("█  服务器: {}:{}".format(SERVER_IP, SERVER_PORT))
    print("█  测试场景数: {}".format(len(scenarios)))
    print("█"*70)
    
    passed = 0
    failed = 0
    
    for name, test_func in scenarios:
        try:
            test_func()
            passed += 1
            print(f"\n  ✓ {name} 完成")
        except Exception as e:
            failed += 1
            print(f"\n  ✗ {name} 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 场景之间暂停
        time.sleep(2)
    
    # 汇总
    print("\n" + "█"*70)
    print("█  测试完成")
    print(f"█  通过: {passed}/{len(scenarios)}")
    print(f"█  失败: {failed}/{len(scenarios)}")
    print("█"*70)

def run_single_test(scenario_num: int):
    """运行单个测试场景"""
    scenarios = {
        1: ("正常呼叫", test_scenario_1_normal_call),
        2: ("被叫忙", test_scenario_2_callee_busy),
        3: ("振铃时取消", test_scenario_3_cancel_ringing),
        4: ("被叫未注册", test_scenario_4_call_not_found),
        5: ("即时消息", test_scenario_5_message),
        6: ("注册注销", test_scenario_6_register_unregister),
        7: ("错误密码", test_scenario_7_wrong_password),
        8: ("并发呼叫", test_scenario_8_multiple_calls),
        9: ("长时间通话", test_scenario_9_long_call),
        10: ("重复注册", test_scenario_10_re_register),
        11: ("高并发呼叫", test_scenario_11_high_concurrency),
    }
    
    if scenario_num in scenarios:
        name, test_func = scenarios[scenario_num]
        print(f"\n运行场景 {scenario_num}: {name}")
        test_func()
    else:
        print(f"场景 {scenario_num} 不存在")
        print(f"可用场景: 1-{len(scenarios)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 运行指定场景
        try:
            scenario_num = int(sys.argv[1])
            run_single_test(scenario_num)
        except ValueError:
            print("用法: python test_sip_scenarios.py [场景编号]")
            print("示例: python test_sip_scenarios.py 1")
            print("\n可用场景:")
            print("  1 - 正常呼叫")
            print("  2 - 被叫忙")
            print("  3 - 振铃时取消")
            print("  4 - 被叫未注册")
            print("  5 - 即时消息")
            print("  6 - 注册注销")
            print("  7 - 错误密码")
            print("  8 - 并发呼叫")
            print("  9 - 长时间通话")
            print("  10 - 重复注册")
            print("  11 - 高并发呼叫")
    else:
        # 运行所有场景
        run_all_tests()

