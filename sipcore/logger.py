# sipcore/logger.py
"""
SIP服务器日志模块
提供统一的日志记录功能，支持控制台和文件输出
按日期分文件夹存储日志，避免单个文件过大

日志格式（遵循业界最佳实践）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
时间戳            级别      文件名:函数名:行号            消息内容
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

示例：
2025-10-29 14:30:45.123 [INFO    ] [run.py:handle_register:245] User 1001 registered successfully
2025-10-29 14:30:45.456 [DEBUG   ] [sip_parser.py:parse_message:89] Parsing SIP message
2025-10-29 14:30:45.789 [WARNING ] [auth.py:check_auth:156] Authentication failed for user 1002
2025-10-29 14:30:46.012 [ERROR   ] [cdr.py:write_record:423] Failed to write CDR: disk full

特性：
- ✅ 毫秒级时间戳（精确到毫秒）
- ✅ 对齐的日志级别（固定8字符宽度）
- ✅ 源代码位置（文件名:函数名:行号）
- ✅ 彩色控制台输出（可选）
- ✅ 按日期分文件夹存储
- ✅ 支持 DEBUG, INFO, WARNING, ERROR, CRITICAL 级别
"""
import logging
import logging.handlers
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class EnhancedFormatter(logging.Formatter):
    """
    增强的日志格式化器
    - 支持毫秒级时间戳
    - 遵循业界最佳实践
    """
    
    def formatTime(self, record, datefmt=None):
        """
        重写时间格式化方法，添加毫秒支持
        格式：YYYY-MM-DD HH:MM:SS.mmm
        """
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S")
        # 添加毫秒
        s = f"{s}.{int(record.msecs):03d}"
        return s


class ColoredFormatter(EnhancedFormatter):
    """彩色日志格式化器（基于增强格式化器）"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 关键：创建 record 的副本，避免修改原始 record 影响其他 handler
        # 因为同一个 LogRecord 对象会被多个 handler 共享（控制台、文件、WebSocket）
        import copy
        record_copy = copy.copy(record)
        log_color = self.COLORS.get(record_copy.levelname, self.RESET)
        record_copy.levelname = f"{log_color}{record_copy.levelname}{self.RESET}"
        return super().format(record_copy)


class DailyRotatingFileHandler(logging.Handler):
    """
    按日期分文件夹的日志处理器
    - 每天创建一个新的日志文件夹（logs/YYYY-MM-DD/）
    - 日志文件保存在对应日期的文件夹中
    - 自动切换到新的日期文件夹
    """
    
    def __init__(self, base_dir: str = "logs", filename: str = "ims-sip-server.log", encoding: str = 'utf-8'):
        """
        初始化日志处理器
        
        Args:
            base_dir: 日志基础目录
            filename: 日志文件名（不含路径）
            encoding: 文件编码
        """
        super().__init__()
        self.base_dir = base_dir
        self.filename = filename
        self.encoding = encoding
        self.current_date = None
        self.current_handler = None
        self._ensure_handler()
    
    def _ensure_handler(self):
        """确保有正确的日志文件处理器"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 如果日期变了，需要切换到新的日志文件
        if self.current_date != today:
            # 创建日期文件夹
            date_dir = os.path.join(self.base_dir, today)
            os.makedirs(date_dir, exist_ok=True)
            
            # 日志文件完整路径
            log_file = os.path.join(date_dir, self.filename)
            
            # 关闭旧的处理器
            if self.current_handler:
                self.current_handler.close()
            
            # 创建新的文件处理器
            self.current_handler = logging.FileHandler(log_file, encoding=self.encoding)
            # 如果已经设置了 formatter，应用到内部 handler
            if self.formatter:
                self.current_handler.setFormatter(self.formatter)
            self.current_handler.setLevel(self.level)
            
            self.current_date = today
    
    def setFormatter(self, fmt):
        """
        设置格式化器
        重写此方法以确保内部 FileHandler 也使用相同的格式化器
        """
        super().setFormatter(fmt)
        # 同时设置内部 handler 的 formatter
        if self.current_handler:
            self.current_handler.setFormatter(fmt)
    
    def emit(self, record):
        """发出日志记录"""
        try:
            # 确保使用正确日期的处理器
            self._ensure_handler()
            # 使用当前处理器记录日志
            self.current_handler.emit(record)
        except Exception:
            self.handleError(record)
    
    def close(self):
        """关闭处理器"""
        if self.current_handler:
            self.current_handler.close()
        super().close()


def setup_logger(
    name: str = "ims-sip-server",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    console_color: bool = True
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选，格式: logs/ims-sip-server.log）
        console: 是否输出到控制台
        console_color: 控制台输出是否使用颜色
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除已有的handlers，确保使用新格式
    # 这样可以在重启或重新配置时应用最新的格式化器
    if logger.handlers:
        logger.handlers.clear()
    
    # 日志格式（业界最佳实践）
    # 格式：时间戳(含毫秒) [级别] [文件名:函数名:行号] 消息内容
    # 示例：2025-10-29 14:30:45.123 [INFO] [run.py:handle_register:245] User 1001 registered
    log_format = '%(asctime)s [%(levelname)-8s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        if console_color:
            formatter = ColoredFormatter(log_format, date_format)
        else:
            formatter = EnhancedFormatter(log_format, date_format)
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件输出（按日期分文件夹）
    if log_file:
        # 解析日志文件路径，提取基础目录和文件名
        # 例如: "logs/ims-sip-server.log" -> base_dir="logs", filename="ims-sip-server.log"
        log_path = Path(log_file)
        base_dir = str(log_path.parent) if log_path.parent != Path('.') else 'logs'
        filename = log_path.name
        
        # 使用按日期分文件夹的处理器
        file_handler = DailyRotatingFileHandler(base_dir=base_dir, filename=filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别的日志
        file_formatter = EnhancedFormatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class SIPLogger:
    """
    SIP服务器专用日志包装类
    提供更易用的日志记录方法
    """
    
    def __init__(self, name: str = "ims-sip-server"):
        self.logger = logging.getLogger(name)
    
    def debug(self, msg: str, *args, **kwargs):
        """DEBUG 级别日志"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """INFO 级别日志"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """WARNING 级别日志"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """ERROR 级别日志"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """CRITICAL 级别日志"""
        self.logger.critical(msg, *args, **kwargs)
    
    # SIP专用日志方法
    def rx(self, addr: tuple, msg: str):
        """记录接收到的消息"""
        self.info(f"[RX] {addr[0]}:{addr[1]} -> {msg}")
    
    def tx(self, addr: tuple, msg: str, extra: str = ""):
        """记录发送的消息"""
        extra_str = f" ({extra})" if extra else ""
        self.info(f"[TX] {addr[0]}:{addr[1]} <- {msg}{extra_str}")
    
    def fwd(self, method_or_msg: str, target: tuple, details: str = ""):
        """记录转发消息"""
        self.info(f"[FWD] {method_or_msg} -> {target[0]}:{target[1]} {details}")
    
    def route(self, method: str, target: tuple):
        """记录路由决策"""
        self.debug(f"[ROUTE] {method} next hop -> {target[0]}:{target[1]}")
    
    def drop(self, reason: str):
        """记录丢弃的消息"""
        self.warning(f"[DROP] {reason}")
    
    def auth(self, username: str, success: bool, reason: str = ""):
        """记录认证结果"""
        status = "SUCCESS" if success else "FAILED"
        extra = f": {reason}" if reason else ""
        self.info(f"[AUTH] User: {username}, Status: {status}{extra}")
    
    def register(self, aor: str, action: str, contact: str = ""):
        """记录注册操作"""
        if contact:
            self.info(f"[REG] AOR: {aor}, Action: {action}, Contact: {contact}")
        else:
            self.info(f"[REG] AOR: {aor}, Action: {action}")
    
    def call(self, call_id: str, event: str, details: str = ""):
        """记录呼叫事件"""
        self.info(f"[CALL] ID: {call_id}, Event: {event}, Details: {details}")


# 全局日志实例
def get_logger(name: str = "ims-sip-server") -> SIPLogger:
    """获取日志记录器实例"""
    return SIPLogger(name)


def init_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> SIPLogger:
    """
    初始化日志系统
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        console: 是否输出到控制台
        
    Returns:
        配置好的日志记录器
    """
    setup_logger(
        name="ims-sip-server",
        level=level,
        log_file=log_file,
        console=console,
        console_color=True
    )
    return get_logger("ims-sip-server")

