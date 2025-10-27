"""
CDR (Call Detail Record) 话单系统
参考业界标准（3GPP TS 32.250/32.260、RFC 7866）实现
支持计费、对账、问题排查等场景
"""

import os
import csv
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class CDRType:
    """CDR 记录类型"""
    REGISTER = "REGISTER"          # 注册
    REGISTER_SUCCESS = "REGISTER_SUCCESS"  # 注册成功
    REGISTER_FAIL = "REGISTER_FAIL"        # 注册失败
    UNREGISTER = "UNREGISTER"      # 注销
    CALL_START = "CALL_START"      # 呼叫开始（INVITE）
    CALL_ANSWER = "CALL_ANSWER"    # 呼叫应答（200 OK）
    CALL_END = "CALL_END"          # 呼叫结束（BYE）
    CALL_FAIL = "CALL_FAIL"        # 呼叫失败（4xx/5xx/6xx）
    CALL_CANCEL = "CALL_CANCEL"    # 呼叫取消（CANCEL）
    MESSAGE = "MESSAGE"            # 短信/消息
    OPTIONS = "OPTIONS"            # 心跳/能力查询
    SUBSCRIBE = "SUBSCRIBE"        # 订阅
    NOTIFY = "NOTIFY"              # 通知


class CDRWriter:
    """
    CDR 写入器（合并模式）
    - 同一个 call_id 的多次事件合并到一条记录
    - 自动按日期创建文件夹和文件
    - 线程安全
    - CSV 格式，易于导入数据库和 Excel
    """
    
    # CDR 字段定义（参考3GPP标准，优化为合并模式）
    FIELDS = [
        "record_id",           # 记录唯一ID
        "record_type",         # 记录类型（CALL/REGISTER/MESSAGE/OPTIONS）
        "call_state",          # 呼叫状态（STARTED/RINGING/ANSWERED/ENDED/FAILED/CANCELLED）
        "date",                # 日期（YYYY-MM-DD）
        "start_time",          # 开始时间（HH:MM:SS）
        "end_time",            # 结束时间（HH:MM:SS）
        "call_id",             # SIP Call-ID
        "caller_uri",          # 主叫URI（From）
        "caller_number",       # 主叫号码
        "caller_ip",           # 主叫IP
        "caller_port",         # 主叫端口
        "callee_uri",          # 被叫URI（To）
        "callee_number",       # 被叫号码
        "callee_ip",           # 被叫IP
        "callee_port",         # 被叫端口
        "duration",            # 通话时长（秒）
        "setup_time",          # 呼叫建立时间（ms）
        "status_code",         # SIP 最终状态码
        "status_text",         # 状态描述
        "termination_reason",  # 终止原因
        "invite_time",         # INVITE 时间
        "ringing_time",        # 180 Ringing 时间
        "answer_time",         # 200 OK 时间
        "bye_time",            # BYE 时间
        "user_agent",          # 用户代理
        "contact",             # Contact 地址
        "expires",             # 过期时间（注册）
        "message_body",        # 消息内容（短信）
        "server_ip",           # 服务器IP
        "server_port",         # 服务器端口
        "cseq",                # CSeq
        "extra_info",          # 额外信息
    ]
    
    def __init__(self, base_dir: str = "CDR", merge_mode: bool = True):
        """
        初始化 CDR 写入器
        
        Args:
            base_dir: CDR 文件根目录
            merge_mode: 是否启用合并模式（同一 call_id 合并为一条记录）
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.record_counter = 0
        self.merge_mode = merge_mode
        
        # 会话跟踪（用于计算通话时长和合并记录）
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # 记录缓存（merge_mode=True 时使用）
        # key: call_id, value: record dict
        self.record_cache: Dict[str, Dict[str, Any]] = {}
        
        # 已写入的记录（防止重复写入）
        # key: call_id, value: record_type (CALL/REGISTER/MESSAGE/OPTIONS)
        self.flushed_records: Dict[str, str] = {}
        
    def _get_daily_file(self) -> Path:
        """获取当天的 CDR 文件路径"""
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        date_dir = self.base_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        csv_file = date_dir / f"cdr_{date_str}.csv"
        
        # 如果文件不存在，写入表头
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writeheader()
        
        return csv_file
    
    def _generate_record_id(self) -> str:
        """生成唯一的记录ID"""
        with self.lock:
            self.record_counter += 1
            return f"{datetime.now().strftime('%Y%m%d%H%M%S')}{self.record_counter:06d}"
    
    def _extract_number(self, uri: str) -> str:
        """从 SIP URI 中提取号码"""
        if not uri:
            return ""
        # 匹配 sip:1001@xxx 或 <sip:1001@xxx>
        import re
        match = re.search(r'sip:([^@;>]+)', uri)
        return match.group(1) if match else ""
    
    def _extract_domain(self, uri: str) -> str:
        """从 SIP URI 中提取域名"""
        if not uri:
            return ""
        import re
        match = re.search(r'@([^;>]+)', uri)
        return match.group(1) if match else ""
    
    def _update_or_create_record(self, call_id: str, **updates):
        """
        更新或创建记录（合并模式）
        
        Args:
            call_id: Call-ID
            **updates: 要更新的字段
        """
        now = datetime.now()
        
        # 获取或创建记录
        if call_id in self.record_cache:
            record = self.record_cache[call_id]
        else:
            # 创建新记录
            record = {field: "" for field in self.FIELDS}
            record["record_id"] = self._generate_record_id()
            record["call_id"] = call_id
            record["date"] = now.strftime("%Y-%m-%d")
            record["start_time"] = now.strftime("%H:%M:%S")
            self.record_cache[call_id] = record
        
        # 更新字段
        for key, value in updates.items():
            if key in self.FIELDS and value:  # 只更新非空值
                record[key] = value
        
        # 自动提取号码
        if record.get("caller_uri") and not record.get("caller_number"):
            record["caller_number"] = self._extract_number(record["caller_uri"])
        if record.get("callee_uri") and not record.get("callee_number"):
            record["callee_number"] = self._extract_number(record["callee_uri"])
        
        # 更新结束时间
        record["end_time"] = now.strftime("%H:%M:%S")
    
    def flush_record(self, call_id: str, force: bool = False):
        """
        将缓存的记录写入文件并清除缓存
        
        Args:
            call_id: Call-ID
            force: 强制写入（忽略重复检查）
        """
        if call_id not in self.record_cache:
            return
        
        with self.lock:
            # 检查是否已经写入过（防止重传导致的重复写入）
            record = self.record_cache[call_id]
            record_type = record.get("record_type", "")
            
            if not force and call_id in self.flushed_records:
                # 已经写入过，忽略（但清除缓存）
                self.record_cache.pop(call_id)
                return
            
            # 写入文件
            record = self.record_cache.pop(call_id)
            csv_file = self._get_daily_file()
            
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writerow(record)
            
            # 标记为已写入（包含时间戳，用于后续清理）
            self.flushed_records[call_id] = {
                "record_type": record_type,
                "timestamp": datetime.now().timestamp()
            }
    
    def cleanup_flushed_records(self, max_age: int = 3600):
        """
        清理旧的已写入记录标记（避免内存无限增长）
        
        Args:
            max_age: 最大保留时间（秒），默认 1 小时
        """
        now = datetime.now().timestamp()
        with self.lock:
            # 删除超过 max_age 的记录标记
            to_remove = [
                call_id for call_id, info in self.flushed_records.items()
                if now - info["timestamp"] > max_age
            ]
            for call_id in to_remove:
                del self.flushed_records[call_id]
            
            if to_remove:
                # 使用 get_logger 而不是 log（因为可能还没初始化）
                try:
                    from .logger import get_logger
                    log = get_logger()
                    log.debug(f"[CDR-CLEANUP] Cleaned {len(to_remove)} old flushed records")
                except:
                    pass
    
    def flush_all_records(self):
        """将所有缓存的记录写入文件"""
        call_ids = list(self.record_cache.keys())
        for call_id in call_ids:
            self.flush_record(call_id)
        
        # 清理旧的已写入标记
        self.cleanup_flushed_records()
    
    def write_record(self, record_type: str, **kwargs):
        """
        写入 CDR 记录（兼容旧接口，用于非合并场景）
        
        Args:
            record_type: 记录类型（使用 CDRType 常量）
            **kwargs: CDR 字段值
        """
        now = datetime.now()
        
        # 构建记录
        record = {field: kwargs.get(field, "") for field in self.FIELDS}
        
        # 设置默认值
        record.update({
            "record_id": self._generate_record_id(),
            "record_type": record_type,
            "date": now.strftime("%Y-%m-%d"),
            "start_time": now.strftime("%H:%M:%S"),
            "end_time": now.strftime("%H:%M:%S"),
        })
        
        # 更新提供的字段
        record.update(kwargs)
        
        # 自动提取号码
        if record.get("caller_uri") and not record.get("caller_number"):
            record["caller_number"] = self._extract_number(record["caller_uri"])
        if record.get("callee_uri") and not record.get("callee_number"):
            record["callee_number"] = self._extract_number(record["callee_uri"])
        
        # 写入文件（线程安全）
        with self.lock:
            csv_file = self._get_daily_file()
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writerow(record)
    
    def start_session(self, call_id: str, **session_info):
        """
        开始会话跟踪
        
        Args:
            call_id: Call-ID
            **session_info: 会话信息
        """
        self.sessions[call_id] = {
            "start_time": datetime.now(),
            **session_info
        }
    
    def end_session(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        结束会话跟踪并返回会话信息
        
        Args:
            call_id: Call-ID
            
        Returns:
            会话信息（包含duration）或 None
        """
        if call_id not in self.sessions:
            return None
        
        session = self.sessions.pop(call_id)
        session["end_time"] = datetime.now()
        
        # 计算时长
        duration = (session["end_time"] - session["start_time"]).total_seconds()
        session["duration"] = round(duration, 2)
        
        return session
    
    def get_session(self, call_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self.sessions.get(call_id)
    
    # ====== 便捷方法：记录各类事件 ======
    
    def record_register(self, caller_uri: str, caller_addr: tuple, 
                       contact: str, expires: int, success: bool = True,
                       status_code: int = 200, status_text: str = "OK",
                       **kwargs):
        """记录注册事件（合并模式：同一个 call-id 只保留最终结果）"""
        call_state = "SUCCESS" if success else "FAILED"
        call_id = kwargs.pop('call_id', f"register-{caller_uri}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        
        # 使用合并模式，同一个 call-id 的多次注册尝试合并为一条记录
        self._update_or_create_record(
            call_id=call_id,
            record_type="REGISTER",
            call_state=call_state,
            caller_uri=caller_uri,
            caller_ip=caller_addr[0],
            caller_port=caller_addr[1],
            contact=contact,
            expires=expires,
            status_code=status_code,
            status_text=status_text,
            **kwargs
        )
        
        # 注册完成，立即写入文件
        self.flush_record(call_id)
    
    def record_unregister(self, caller_uri: str, caller_addr: tuple, 
                         contact: str, **kwargs):
        """记录注销事件（合并模式）"""
        call_id = kwargs.pop('call_id', f"unregister-{caller_uri}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        
        # 使用合并模式
        self._update_or_create_record(
            call_id=call_id,
            record_type="REGISTER",
            call_state="UNREGISTERED",
            caller_uri=caller_uri,
            caller_ip=caller_addr[0],
            caller_port=caller_addr[1],
            contact=contact,
            expires=0,
            status_code=200,
            status_text="OK",
            **kwargs
        )
        
        # 注销完成，立即写入文件
        self.flush_record(call_id)
    
    def record_call_start(self, call_id: str, caller_uri: str, callee_uri: str,
                         caller_addr: tuple, **kwargs):
        """记录呼叫开始（INVITE）"""
        # 开始会话跟踪
        self.start_session(call_id, 
                          caller_uri=caller_uri,
                          callee_uri=callee_uri,
                          caller_addr=caller_addr)
        
        now = datetime.now()
        self._update_or_create_record(
            call_id=call_id,
            record_type="CALL",
            call_state="STARTED",
            caller_uri=caller_uri,
            callee_uri=callee_uri,
            caller_ip=caller_addr[0],
            caller_port=caller_addr[1],
            invite_time=now.strftime("%H:%M:%S.%f")[:-3],
            **kwargs
        )
        # 不立即 flush，等待后续更新
    
    def record_call_answer(self, call_id: str, callee_addr: tuple, 
                          setup_time: float = 0, **kwargs):
        """记录呼叫应答（200 OK）"""
        session = self.get_session(call_id)
        if session:
            session["answer_time"] = datetime.now()
            if setup_time == 0 and "start_time" in session:
                setup_time = (session["answer_time"] - session["start_time"]).total_seconds() * 1000
        
        now = datetime.now()
        self._update_or_create_record(
            call_id=call_id,
            call_state="ANSWERED",
            callee_ip=callee_addr[0],
            callee_port=callee_addr[1],
            setup_time=round(setup_time, 2) if setup_time else "",
            answer_time=now.strftime("%H:%M:%S.%f")[:-3],
            status_code=200,
            status_text="OK",
            **kwargs
        )
        # 不立即 flush，等待 BYE
    
    def record_call_end(self, call_id: str, termination_reason: str = "Normal", **kwargs):
        """记录呼叫结束（BYE）"""
        session = self.end_session(call_id)
        
        now = datetime.now()
        updates = {
            "call_state": "ENDED",
            "bye_time": now.strftime("%H:%M:%S.%f")[:-3],
            "termination_reason": termination_reason,
            **kwargs
        }
        
        if session:
            updates["duration"] = session.get("duration", 0)
        
        self._update_or_create_record(call_id=call_id, **updates)
        # 呼叫结束，立即写入文件
        self.flush_record(call_id)
    
    def record_call_fail(self, call_id: str, status_code: int, status_text: str,
                        reason: str = "", **kwargs):
        """记录呼叫失败"""
        session = self.end_session(call_id)
        
        self._update_or_create_record(
            call_id=call_id,
            call_state="FAILED",
            status_code=status_code,
            status_text=status_text,
            termination_reason=reason or f"{status_code} {status_text}",
            **kwargs
        )
        # 呼叫失败，立即写入文件
        self.flush_record(call_id)
    
    def record_call_cancel(self, call_id: str, **kwargs):
        """记录呼叫取消（CANCEL）"""
        session = self.end_session(call_id)
        
        self._update_or_create_record(
            call_id=call_id,
            call_state="CANCELLED",
            termination_reason="User Cancelled",
            **kwargs
        )
        # 呼叫取消，立即写入文件
        self.flush_record(call_id)
    
    def record_message(self, call_id: str, caller_uri: str, callee_uri: str,
                      caller_addr: tuple, message_body: str = "", **kwargs):
        """记录短信/消息"""
        self.write_record(
            record_type="MESSAGE",
            call_state="COMPLETED",
            call_id=call_id,
            caller_uri=caller_uri,
            callee_uri=callee_uri,
            caller_ip=caller_addr[0],
            caller_port=caller_addr[1],
            message_body=message_body[:500],  # 限制长度
            status_code=200,
            status_text="OK",
            **kwargs
        )
    
    def record_options(self, caller_uri: str, callee_uri: str, 
                      caller_addr: tuple, **kwargs):
        """记录 OPTIONS 请求"""
        # OPTIONS 使用 call_id 作为唯一标识
        call_id = kwargs.pop('call_id', f"options-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        self.write_record(
            record_type="OPTIONS",
            call_state="COMPLETED",
            call_id=call_id,
            caller_uri=caller_uri,
            callee_uri=callee_uri,
            caller_ip=caller_addr[0],
            caller_port=caller_addr[1],
            status_code=200,
            status_text="OK",
            **kwargs
        )
    
    def get_stats(self, date: str = None) -> Dict[str, int]:
        """
        获取统计信息
        
        Args:
            date: 日期（YYYY-MM-DD），默认今天
            
        Returns:
            统计信息字典
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        csv_file = self.base_dir / date / f"cdr_{date}.csv"
        if not csv_file.exists():
            return {}
        
        stats = {
            "total_records": 0,
            "registers": 0,
            "calls_started": 0,
            "calls_answered": 0,
            "calls_ended": 0,
            "calls_failed": 0,
            "calls_cancelled": 0,
            "messages": 0,
            "options": 0,
        }
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total_records"] += 1
                record_type = row.get("record_type", "")
                call_state = row.get("call_state", "")
                
                if record_type == "REGISTER":
                    stats["registers"] += 1
                elif record_type == "CALL":
                    if call_state == "STARTED":
                        stats["calls_started"] += 1
                    elif call_state == "ANSWERED":
                        stats["calls_answered"] += 1
                    elif call_state == "ENDED":
                        stats["calls_ended"] += 1
                    elif call_state == "FAILED":
                        stats["calls_failed"] += 1
                    elif call_state == "CANCELLED":
                        stats["calls_cancelled"] += 1
                elif record_type == "MESSAGE":
                    stats["messages"] += 1
                elif record_type == "OPTIONS":
                    stats["options"] += 1
        
        return stats


# 全局 CDR 实例
_cdr_instance: Optional[CDRWriter] = None


def init_cdr(base_dir: str = "CDR", merge_mode: bool = True) -> CDRWriter:
    """初始化全局 CDR 实例"""
    global _cdr_instance
    _cdr_instance = CDRWriter(base_dir, merge_mode=merge_mode)
    return _cdr_instance


def get_cdr() -> CDRWriter:
    """获取全局 CDR 实例"""
    global _cdr_instance
    if _cdr_instance is None:
        _cdr_instance = init_cdr()
    return _cdr_instance

