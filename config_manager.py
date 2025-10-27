"""
配置管理模块
支持动态修改配置，不影响业务运行
"""
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class ConfigManager:
    """配置管理器 - 支持动态修改和持久化"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.lock = threading.RLock()
        self._config_cache: Dict[str, Any] = {}
        self._load_config()
        
    def _load_config(self):
        """从文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
            except Exception as e:
                print(f"[CONFIG] Failed to load config: {e}")
                self._config_cache = {}
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_cache, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        with self.lock:
            return self._config_cache.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        with self.lock:
            old_value = self._config_cache.get(key)
            self._config_cache[key] = value
            self._save_config()
            
            # 记录修改
            print(f"[CONFIG] {key}: {old_value} -> {value}")
            return True
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self.lock:
            return self._config_cache.copy()
    
    def update_batch(self, updates: Dict[str, Any]) -> Dict[str, bool]:
        """批量更新配置"""
        results = {}
        with self.lock:
            for key, value in updates.items():
                try:
                    old_value = self._config_cache.get(key)
                    self._config_cache[key] = value
                    print(f"[CONFIG] {key}: {old_value} -> {value}")
                    results[key] = True
                except Exception as e:
                    print(f"[CONFIG] Failed to set {key}: {e}")
                    results[key] = False
            
            # 统一保存
            self._save_config()
        
        return results


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def init_config_manager(config_file: str = "config.json") -> ConfigManager:
    """初始化配置管理器"""
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 可动态修改的配置项定义
DYNAMIC_CONFIG = {
    # 用户管理（可动态修改）
    "USERS": {
        "type": "dict",
        "editable": True,
        "restart_required": False,
        "description": "用户账号和密码",
        "validator": lambda v: isinstance(v, dict) and all(isinstance(k, str) and isinstance(v2, str) for k, v2 in v.items())
    },
    
    # 网络配置（部分可动态修改）
    "FORCE_LOCAL_ADDR": {
        "type": "bool",
        "editable": True,
        "restart_required": False,
        "description": "强制本地地址模式",
        "validator": lambda v: isinstance(v, bool)
    },
    
    "LOCAL_NETWORKS": {
        "type": "list",
        "editable": True,
        "restart_required": False,
        "description": "本地网络地址列表",
        "validator": lambda v: isinstance(v, list) and all(isinstance(i, str) for i in v)
    },
    
    # 日志配置（可动态修改）
    "LOG_LEVEL": {
        "type": "str",
        "editable": True,
        "restart_required": False,
        "description": "日志级别",
        "validator": lambda v: v in ["DEBUG", "INFO", "WARNING", "ERROR"],
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"]
    },
    
    # CDR 配置（可动态修改）
    "CDR_MERGE_MODE": {
        "type": "bool",
        "editable": True,
        "restart_required": False,
        "description": "CDR 记录合并模式",
        "validator": lambda v: isinstance(v, bool)
    },
    
    # 不可动态修改的配置（需要重启）
    "SERVER_IP": {
        "type": "str",
        "editable": False,
        "restart_required": True,
        "description": "服务器 IP 地址（修改需重启）",
        "validator": lambda v: isinstance(v, str)
    },
    
    "SERVER_PORT": {
        "type": "int",
        "editable": False,
        "restart_required": True,
        "description": "服务器端口（修改需重启）",
        "validator": lambda v: isinstance(v, int) and 1024 <= v <= 65535
    },
}


def validate_config(key: str, value: Any) -> tuple[bool, str]:
    """
    验证配置项
    
    Returns:
        (是否有效, 错误消息)
    """
    config_def = DYNAMIC_CONFIG.get(key)
    
    if not config_def:
        return False, f"未知的配置项: {key}"
    
    if not config_def.get("editable", False):
        return False, f"配置项 {key} 不可修改（需要重启服务器）"
    
    # 类型验证
    validator = config_def.get("validator")
    if validator and not validator(value):
        return False, f"配置项 {key} 的值无效"
    
    return True, ""


def apply_config_change(key: str, value: Any) -> tuple[bool, str]:
    """
    应用配置更改到运行时
    
    Returns:
        (是否成功, 消息)
    """
    try:
        # 验证配置
        valid, error_msg = validate_config(key, value)
        if not valid:
            return False, error_msg
        
        # 保存到配置文件
        config_mgr = get_config_manager()
        config_mgr.set(key, value)
        
        # 应用到运行时
        import run
        
        if key == "USERS":
            # 动态更新用户列表
            run.USERS.clear()
            run.USERS.update(value)
            return True, f"用户列表已更新（当前 {len(value)} 个用户）"
        
        elif key == "FORCE_LOCAL_ADDR":
            # 动态更新强制本地模式
            run.FORCE_LOCAL_ADDR = value
            return True, f"强制本地地址模式已{'启用' if value else '禁用'}"
        
        elif key == "LOCAL_NETWORKS":
            # 动态更新本地网络列表
            run.LOCAL_NETWORKS.clear()
            run.LOCAL_NETWORKS.extend(value)
            return True, f"本地网络地址已更新（{len(value)} 个地址）"
        
        elif key == "LOG_LEVEL":
            # 动态更新日志级别
            import logging
            level = getattr(logging, value)
            # 尝试设置日志级别
            try:
                # SIPLogger 包装类，通过 logger 属性访问底层 Logger
                if hasattr(run.log, 'logger') and hasattr(run.log.logger, 'setLevel'):
                    run.log.logger.setLevel(level)
                    # 同时更新所有处理器的级别
                    for handler in run.log.logger.handlers:
                        handler.setLevel(level)
                    return True, f"日志级别已更新为 {value}（立即生效）"
                else:
                    # 如果是标准 Logger 对象
                    if hasattr(run.log, 'setLevel'):
                        run.log.setLevel(level)
                        return True, f"日志级别已更新为 {value}（立即生效）"
                    else:
                        # 保存配置但无法立即应用
                        return True, f"日志级别配置已保存为 {value}（重启后生效）"
            except Exception as e:
                # 出现错误，配置已保存但可能需要重启
                print(f"[CONFIG] Failed to apply LOG_LEVEL: {e}")
                return True, f"日志级别配置已保存为 {value}（重启后生效）"
        
        elif key == "CDR_MERGE_MODE":
            # CDR 合并模式（新创建的 CDR 会使用新设置）
            return True, f"CDR 合并模式已{'启用' if value else '禁用'}（对新记录生效）"
        
        else:
            return False, f"配置项 {key} 暂不支持动态修改"
    
    except Exception as e:
        return False, f"应用配置失败: {str(e)}"


def get_editable_configs() -> Dict[str, Any]:
    """获取所有可编辑的配置项定义"""
    return {
        key: {
            "type": config["type"],
            "description": config["description"],
            "restart_required": config["restart_required"],
            "options": config.get("options")
        }
        for key, config in DYNAMIC_CONFIG.items()
        if config.get("editable", False)
    }

