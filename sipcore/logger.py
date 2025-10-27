# sipcore/logger.py
"""
SIP服务器日志模块
提供统一的日志记录功能，支持控制台和文件输出
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


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
        log_file: 日志文件路径（可选）
        console: 是否输出到控制台
        console_color: 控制台输出是否使用颜色
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        if console_color:
            formatter = ColoredFormatter(log_format, date_format)
        else:
            formatter = logging.Formatter(log_format, date_format)
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别的日志
        file_formatter = logging.Formatter(log_format, date_format)
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

