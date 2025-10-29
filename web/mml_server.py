"""
MML (Man-Machine Language) 管理界面服务器

类似华为网管界面的 MML 命令行管理系统
- 左侧：命令树
- 中间：命令输入/输出
- 右侧：实时日志
"""

import asyncio
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import os
import sys
import queue
import logging
import re

# WebSocket 支持
try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[WARNING] websockets not installed, real-time logs disabled")
    print("Install: pip install websockets")


# 日志订阅器集合（用于实时推送日志）
log_subscribers = set()
# 日志消息队列（用于线程安全的日志传递）
log_queue = queue.Queue(maxsize=1000)


class MMLCommandTree:
    """MML 命令树定义"""
    
    @staticmethod
    def get_command_tree():
        """获取命令树结构"""
        return {
            "系统管理": {
                "icon": "⚙️",
                "commands": {
                    "查询系统状态": "DSP SYSINFO",
                    "查询系统配置": "DSP SYSCFG",
                    "修改日志级别": "SET LOGLEVEL",
                    "查询服务状态": "DSP SRVSTAT",
                    "重启服务": "RST SERVICE CONFIRM=YES"
                }
            },
            "用户管理": {
                "icon": "👤",
                "commands": {
                    "查询所有用户": "DSP USER ALL",
                    "查询指定用户": "DSP USER",
                    "添加用户": "ADD USER",
                    "删除用户": "RMV USER",
                    "修改用户": "MOD USER"
                }
            },
            "注册管理": {
                "icon": "📝",
                "commands": {
                    "查询注册列表": "DSP REG ALL",
                    "查询指定注册": "DSP REG SPECIFIC",
                    "查询注册统计": "DSP REG STAT",
                    "强制注销": "RMV REG SPECIFIC",
                    "清除所有注册": "CLR REG ALL CONFIRM=YES"
                }
            },
            "呼叫管理": {
                "icon": "📞",
                "commands": {
                    "查询活跃呼叫": "DSP CALL ACTIVE",
                    "查询呼叫统计": "DSP CALL STAT",
                    "查询指定呼叫": "DSP CALL CALLID={call_id}",
                    "强制挂断": "RMV CALL CALLID={call_id} CONFIRM=YES",
                    "清除所有呼叫": "CLR CALL ALL CONFIRM=YES"
                }
            },
            "CDR 管理": {
                "icon": "📊",
                "commands": {
                    "查询今日 CDR": "DSP CDR TODAY",
                    "查询指定日期 CDR": "DSP CDR",
                    "查询 CDR 统计": "DSP CDR STAT",
                    "导出 CDR": "EXP CDR",
                    "清理旧 CDR": "CLR CDR"
                }
            },
            "配置管理": {
                "icon": "🔧",
                "commands": {
                    "查询所有配置": "DSP CFG ALL",
                    "查询指定配置": "DSP CFG KEY={key}",
                    "修改配置": "SET CFG KEY={key} VALUE={value}",
                    "重置配置": "RST CFG KEY={key} CONFIRM=YES",
                    "保存配置": "SAVE CFG"
                }
            },
            "性能监控": {
                "icon": "📈",
                "commands": {
                    "查询性能指标": "DSP PERF ALL",
                    "查询 CPU 使用": "DSP PERF CPU",
                    "查询内存使用": "DSP PERF MEM",
                    "查询网络流量": "DSP PERF NET",
                    "查询消息统计": "DSP PERF MSG"
                }
            },
            "日志管理": {
                "icon": "📋",
                "commands": {
                    "查询日志配置": "DSP LOG CFG",
                    "修改日志级别": "SET LOG",
                    "查询最近日志": "DSP LOG RECENT LINES={n}",
                    "搜索日志": "DSP LOG SEARCH KEYWORD={keyword}",
                    "清理日志": "CLR LOG BEFORE={date} CONFIRM=YES"
                }
            },
            "帮助信息": {
                "icon": "❓",
                "commands": {
                    "显示所有命令": "HELP ALL",
                    "显示命令帮助": "HELP CMD={command}",
                    "显示参数说明": "HELP PARAM={parameter}",
                    "显示快捷键": "HELP HOTKEY"
                }
            }
        }


class MMLCommandExecutor:
    """MML 命令执行器"""
    
    def __init__(self, server_globals=None):
        self.server_globals = server_globals or {}
        self.command_handlers = {
            "DSP": self._handle_display,
            "ADD": self._handle_add,
            "RMV": self._handle_remove,
            "MOD": self._handle_modify,
            "SET": self._handle_set,
            "CLR": self._handle_clear,
            "RST": self._handle_reset,
            "EXP": self._handle_export,
            "SAVE": self._handle_save,
            "HELP": self._handle_help,
        }
    
    def execute(self, command_line):
        """执行 MML 命令"""
        try:
            # 解析命令
            parts = command_line.strip().split()
            if not parts:
                return self._error_response("空命令")
            
            verb = parts[0].upper()
            
            if verb not in self.command_handlers:
                return self._error_response(f"未知命令: {verb}")
            
            # 执行命令
            handler = self.command_handlers[verb]
            result = handler(parts)
            
            return result
            
        except Exception as e:
            return self._error_response(f"命令执行错误: {str(e)}")
    
    def _parse_params(self, parts):
        """解析命令参数"""
        params = {}
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.upper()] = value
        return params
    
    def _handle_display(self, parts):
        """处理 DSP (Display) 命令"""
        if len(parts) < 2:
            return self._error_response("DSP 命令需要指定对象")
        
        obj = parts[1].upper()
        
        # 特殊处理：DSP CALL STAT -> DSP CALL SUBTYPE=STAT
        if len(parts) > 2 and parts[2].upper() in ['STAT', 'ACTIVE']:
            parts = parts[:2] + [f"SUBTYPE={parts[2].upper()}"] + parts[3:]
        
        # 特殊处理：DSP REG STAT -> DSP REG SUBTYPE=STAT
        if len(parts) > 2 and obj == 'REG' and parts[2].upper() == 'STAT':
            parts = parts[:2] + [f"SUBTYPE=STAT"] + parts[3:]
        
        # 特殊处理：DSP CDR STAT -> DSP CDR SUBTYPE=STAT
        # 特殊处理：DSP CDR TODAY -> DSP CDR DATE=TODAY
        if obj == 'CDR' and len(parts) > 2:
            if parts[2].upper() == 'STAT':
                parts = parts[:2] + [f"SUBTYPE=STAT"] + parts[3:]
            elif parts[2].upper() == 'TODAY':
                parts = parts[:2] + [f"DATE=TODAY"] + parts[3:]
        
        params = self._parse_params(parts[2:])
        
        # 获取服务器全局状态
        if not self.server_globals:
            return self._error_response("服务器状态不可用")
        
        if obj == "SYSINFO":
            return self._display_sysinfo(self.server_globals)
        elif obj == "SYSCFG":
            return self._display_syscfg(self.server_globals)
        elif obj == "USER":
            # 区分：DSP USER = 查询已开户用户，DSP REG = 查询已注册用户
            return self._display_users(params)
        elif obj == "REG":
            return self._display_registrations(self.server_globals, params)
        elif obj == "CALL":
            return self._display_calls(self.server_globals, params)
        elif obj == "CDR":
            return self._display_cdr(params)
        elif obj == "CFG":
            return self._display_config(self.server_globals, params)
        elif obj == "PERF":
            return self._display_performance(self.server_globals, params)
        elif obj == "LOG":
            return self._display_logs(params)
        elif obj == "SRVSTAT":
            return self._display_service_status(self.server_globals)
        else:
            return self._error_response(f"未知对象: {obj}")
    
    def _display_sysinfo(self, srv):
        """显示系统信息"""
        import platform
        from datetime import datetime
        
        output = [
            "=" * 60,
            "系统信息",
            "=" * 60,
            f"服务器名称    : IMS SIP Server",
            f"版本          : 2.0.0",
            f"操作系统      : {platform.system()} {platform.release()}",
            f"Python 版本   : {platform.python_version()}",
            f"服务器 IP     : {srv.get('SERVER_IP', 'N/A')}",
            f"服务器端口    : {srv.get('SERVER_PORT', 'N/A')}",
        ]
        
        # 尝试获取系统信息（需要 psutil）
        try:
            import psutil
            uptime = time.time() - psutil.boot_time()
            output.append(f"系统运行时间  : {int(uptime/3600)}小时{int((uptime%3600)/60)}分钟")
            output.append(f"CPU 核心数    : {psutil.cpu_count()}")
            output.append(f"总内存        : {psutil.virtual_memory().total / (1024**3):.2f} GB")
        except ImportError:
            import os
            output.append(f"CPU 核心数    : {os.cpu_count() or 'N/A'}")
            output.append(f"总内存        : N/A (需要安装 psutil)")
        
        output.append("=" * 60)
        
        return self._success_response("\n".join(output))
    
    def _display_syscfg(self, srv):
        """显示系统配置"""
        output = [
            "=" * 60,
            "系统配置",
            "=" * 60,
            f"SERVER_IP              : {srv.get('SERVER_IP', 'N/A')}",
            f"SERVER_PORT            : {srv.get('SERVER_PORT', 'N/A')}",
            f"MAX_FORWARDS           : {srv.get('MAX_FORWARDS', 'N/A')}",
            f"REGISTRATION_EXPIRES   : {srv.get('REGISTRATION_EXPIRES', 'N/A')}",
            f"FORCE_LOCAL_ADDR       : {srv.get('FORCE_LOCAL_ADDR', 'N/A')}",
            "=" * 60,
        ]
        
        return self._success_response("\n".join(output))
    
    def _display_users(self, params):
        """显示已开户用户信息（不是注册用户）"""
        from sipcore.user_manager import get_user_manager
        
        user_mgr = get_user_manager()
        username = params.get('USERNAME', '').upper()
        status = params.get('STATUS', '').upper()
        
        if username:
            # 查询单个用户
            user = user_mgr.get_user(username)
            if not user:
                return self._error_response(f"用户 {username} 不存在")
            
            output = [
                "=" * 60,
                "用户详细信息",
                "=" * 60,
                f"用户名        : {user.get('username', 'N/A')}",
                f"显示名称      : {user.get('display_name', 'N/A')}",
                f"电话号码      : {user.get('phone', 'N/A')}",
                f"邮箱          : {user.get('email', 'N/A')}",
                f"状态          : {user.get('status', 'N/A')}",
                f"服务类型      : {user.get('service_type', 'N/A')}",
                f"创建时间      : {user.get('create_time', 'N/A')}",
                f"更新时间      : {user.get('update_time', 'N/A')}",
                "=" * 60,
            ]
        else:
            # 查询所有用户
            filter_status = status if status in ['ACTIVE', 'INACTIVE', 'SUSPENDED'] else None
            users = user_mgr.get_all_users(status=filter_status)
            
            output = [
                "=" * 100,
                "已开户用户列表",
                "=" * 100,
                f"{'用户名':<15} {'显示名称':<20} {'电话':<15} {'邮箱':<25} {'状态':<10} {'服务类型':<10}",
                "-" * 100,
            ]
            
            for user in users:
                username = user.get('username', 'N/A')
                display_name = user.get('display_name', 'N/A')
                phone = user.get('phone', 'N/A')
                email = user.get('email', 'N/A')
                status = user.get('status', 'N/A')
                service_type = user.get('service_type', 'N/A')
                
                output.append(f"{username:<15} {display_name:<20} {phone:<15} {email:<25} {status:<10} {service_type:<10}")
            
            output.append("-" * 100)
            output.append(f"总计: {len(users)} 个用户")
            output.append("=" * 100)
        
        return self._success_response("\n".join(output))
    
    def _display_registrations(self, srv, params):
        """显示注册信息"""
        subtype = params.get('SUBTYPE', 'ALL').upper()
        uri = params.get('URI', '').strip()
        registrations = srv.get('REGISTRATIONS', {})
        
        if subtype == 'STAT':
            # 注册统计
            total_users = len(registrations)
            total_bindings = sum(len(v) for v in registrations.values())
            
            output = [
                "=" * 60,
                "注册统计",
                "=" * 60,
                f"注册用户数     : {total_users}",
                f"注册绑定数     : {total_bindings}",
                f"平均绑定数     : {total_bindings/total_users if total_users > 0 else 0:.2f}",
                "=" * 60,
            ]
        elif uri:
            # 查询指定用户的注册
            # 标准化 URI：如果只输入号码，转换为 sip:xxx@domain 格式
            if '@' not in uri and not uri.startswith('sip:'):
                # 尝试匹配包含该号码的任意 AOR
                matched_aors = [aor for aor in registrations.keys() if uri in aor]
            else:
                # 精确匹配
                matched_aors = [aor for aor in registrations.keys() if aor == uri or aor == f"sip:{uri}"]
            
            if not matched_aors:
                return self._error_response(f"未找到 URI '{uri}' 的注册信息")
            
            output = [
                "=" * 80,
                f"注册详情 - {uri}",
                "=" * 80,
            ]
            
            count = 0
            for aor in matched_aors:
                bindings = registrations.get(aor, [])
                output.append(f"\nAOR: {aor}")
                output.append("-" * 80)
                output.append(f"{'Contact':<50} {'Expires':<10} {'剩余时间':<10}")
                output.append("-" * 80)
                
                for binding in bindings:
                    count += 1
                    contact = binding.get('contact', 'N/A')
                    expires = binding.get('expires', 0)
                    import time
                    remaining = max(0, expires - int(time.time()))
                    remaining_str = f"{remaining}s" if remaining > 0 else "已过期"
                    output.append(f"{contact:<50} {expires:<10} {remaining_str:<10}")
            
            output.append("=" * 80)
            output.append(f"总计: {count} 条注册记录")
            output.append("=" * 80)
        else:
            # 注册列表
            output = [
                "=" * 80,
                "注册列表",
                "=" * 80,
                f"{'AOR':<40} {'Contact':<30} {'Expires':<10}",
                "-" * 80,
            ]
            
            count = 0
            for aor, bindings in registrations.items():
                for binding in bindings:
                    count += 1
                    contact = binding.get('contact', 'N/A')
                    expires = binding.get('expires', 0)
                    output.append(f"{aor:<40} {contact:<30} {expires:<10}")
            
            output.append("-" * 80)
            output.append(f"总计: {count} 条注册记录")
            output.append("=" * 80)
        
        return self._success_response("\n".join(output))
    
    def _display_calls(self, srv, params):
        """显示呼叫信息"""
        subtype = params.get('SUBTYPE', 'ACTIVE').upper()
        dialogs = srv.get('DIALOGS', {})
        pending = srv.get('PENDING_REQUESTS', {})
        branches = srv.get('INVITE_BRANCHES', {})
        
        if subtype == 'STAT':
            # 呼叫统计
            output = [
                "=" * 60,
                "呼叫统计",
                "=" * 60,
                f"活跃呼叫数     : {len(dialogs)}",
                f"待处理请求数   : {len(pending)}",
                f"INVITE分支数   : {len(branches)}",
                "=" * 60,
            ]
        else:
            # 活跃呼叫列表
            output = [
                "=" * 100,
                "活跃呼叫列表",
                "=" * 100,
                f"{'Call-ID':<40} {'Caller':<25} {'Callee':<25} {'状态':<10}",
                "-" * 100,
            ]
            
            count = 0
            for call_id, dialog in dialogs.items():
                count += 1
                # 简化显示
                call_id_short = call_id[:36] + "..." if len(call_id) > 36 else call_id
                output.append(f"{call_id_short:<40} {'N/A':<25} {'N/A':<25} {'ACTIVE':<10}")
            
            output.append("-" * 100)
            output.append(f"总计: {count} 个活跃呼叫")
            output.append("=" * 100)
        
        return self._success_response("\n".join(output))
    
    def _display_service_status(self, srv):
        """显示服务状态"""
        import os
        
        registrations = srv.get('REGISTRATIONS', {})
        dialogs = srv.get('DIALOGS', {})
        pending = srv.get('PENDING_REQUESTS', {})
        
        output = [
            "=" * 60,
            "服务状态",
            "=" * 60,
            f"进程 ID        : {os.getpid()}",
        ]
        
        # 尝试获取进程信息（需要 psutil）
        try:
            import psutil
            process = psutil.Process()
            output.append(f"CPU 使用率     : {process.cpu_percent()}%")
            output.append(f"内存使用       : {process.memory_info().rss / (1024**2):.2f} MB")
            output.append(f"线程数         : {process.num_threads()}")
        except ImportError:
            output.append(f"CPU 使用率     : N/A (需要安装 psutil)")
            output.append(f"内存使用       : N/A (需要安装 psutil)")
            output.append(f"线程数         : N/A (需要安装 psutil)")
        
        output.extend([
            f"活跃注册数     : {sum(len(v) for v in registrations.values())}",
            f"活跃呼叫数     : {len(dialogs)}",
            f"待处理请求     : {len(pending)}",
            "=" * 60,
        ])
        
        return self._success_response("\n".join(output))
    
    def _display_cdr(self, params):
        """显示 CDR"""
        import os
        import csv
        from datetime import datetime
        
        subtype = params.get('SUBTYPE', '').upper()
        date = params.get('DATE', datetime.now().strftime('%Y-%m-%d'))
        if date == 'TODAY':
            date = datetime.now().strftime('%Y-%m-%d')
        
        record_type = params.get('TYPE', '').upper()  # CALL, REGISTER, MESSAGE 等
        limit = int(params.get('LIMIT', 50))
        
        cdr_file = f"CDR/{date}/cdr_{date}.csv"
        
        if not os.path.exists(cdr_file):
            return self._error_response(f"CDR 文件不存在: {cdr_file}")
        
        try:
            # 读取 CDR 数据
            records = []
            with open(cdr_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 类型过滤
                    if record_type and row.get('record_type', '') != record_type:
                        continue
                    records.append(row)
            
            # 统计模式
            if subtype == 'STAT':
                return self._display_cdr_stat(records, date)
            
            # 列表模式
            output = [
                "=" * 150,
                f"CDR 记录 - {date}" + (f" (类型: {record_type})" if record_type else ""),
                "=" * 150,
            ]
            
            if not records:
                output.append("无记录")
                output.append("=" * 150)
                return self._success_response("\n".join(output))
            
            # 表格表头
            header = (
                f"{'序号':<6} {'类型':<12} {'状态':<12} {'时间':<10} "
                f"{'主叫':<18} {'被叫':<18} {'时长':<8} {'结果':<15}"
            )
            output.append(header)
            output.append("-" * 150)
            
            # 显示记录（限制数量）
            for idx, record in enumerate(records[:limit], 1):
                rec_type = record.get('record_type', 'N/A')
                call_state = record.get('call_state', 'N/A')
                start_time = record.get('start_time', 'N/A')
                caller = record.get('caller_uri', 'N/A')
                callee = record.get('callee_uri', 'N/A')
                duration = record.get('duration', '0')
                
                # 截取 URI 显示（去掉 sip: 前缀和域名）
                caller_display = self._format_uri(caller)
                callee_display = self._format_uri(callee)
                
                # 格式化时长
                duration_str = f"{duration}s" if duration and duration != 'N/A' else '-'
                
                # 结果/状态
                if rec_type == 'CALL':
                    if call_state == 'ANSWERED':
                        result = f"已接听 ({record.get('status_code', 'N/A')})"
                    elif call_state == 'FAILED':
                        result = f"失败 ({record.get('status_code', 'N/A')})"
                    elif call_state == 'CANCELLED':
                        result = "已取消"
                    else:
                        result = call_state
                elif rec_type == 'REGISTER':
                    result = f"{record.get('status_code', 'N/A')} {record.get('status_text', '')}"
                else:
                    result = call_state
                
                line = (
                    f"{idx:<6} {rec_type:<12} {call_state:<12} {start_time:<10} "
                    f"{caller_display:<18} {callee_display:<18} {duration_str:<8} {result:<15}"
                )
                output.append(line)
            
            output.append("-" * 150)
            
            # 统计信息
            total = len(records)
            if total > limit:
                output.append(f"显示: {limit}/{total} 条记录 (使用 LIMIT 参数查看更多)")
            else:
                output.append(f"总计: {total} 条记录")
            
            output.append("=" * 150)
            return self._success_response("\n".join(output))
            
        except Exception as e:
            import traceback
            return self._error_response(f"读取 CDR 失败: {str(e)}\n{traceback.format_exc()}")
    
    def _display_cdr_stat(self, records, date):
        """显示 CDR 统计信息"""
        output = [
            "=" * 80,
            f"CDR 统计 - {date}",
            "=" * 80,
        ]
        
        if not records:
            output.append("无记录")
            output.append("=" * 80)
            return self._success_response("\n".join(output))
        
        # 按类型统计
        type_stats = {}
        state_stats = {}
        total_duration = 0
        answered_calls = 0
        
        for record in records:
            rec_type = record.get('record_type', 'UNKNOWN')
            call_state = record.get('call_state', 'UNKNOWN')
            
            # 类型统计
            type_stats[rec_type] = type_stats.get(rec_type, 0) + 1
            
            # 状态统计
            state_stats[call_state] = state_stats.get(call_state, 0) + 1
            
            # 时长统计（只统计呼叫）
            if rec_type == 'CALL' and call_state == 'ANSWERED':
                try:
                    duration = int(record.get('duration', 0) or 0)
                    total_duration += duration
                    answered_calls += 1
                except:
                    pass
        
        # 输出统计
        output.append("\n【记录类型统计】")
        output.append("-" * 80)
        for rec_type, count in sorted(type_stats.items()):
            percentage = count / len(records) * 100
            output.append(f"  {rec_type:<20} : {count:>6} 条 ({percentage:>5.1f}%)")
        
        output.append("\n【呼叫状态统计】")
        output.append("-" * 80)
        for state, count in sorted(state_stats.items()):
            percentage = count / len(records) * 100
            output.append(f"  {state:<20} : {count:>6} 条 ({percentage:>5.1f}%)")
        
        # 呼叫时长统计
        if answered_calls > 0:
            avg_duration = total_duration / answered_calls
            output.append("\n【呼叫时长统计】")
            output.append("-" * 80)
            output.append(f"  接通呼叫数          : {answered_calls} 次")
            output.append(f"  总通话时长          : {total_duration} 秒 ({total_duration//60} 分钟)")
            output.append(f"  平均通话时长        : {avg_duration:.1f} 秒")
        
        output.append("\n【总体统计】")
        output.append("-" * 80)
        output.append(f"  总记录数            : {len(records)}")
        output.append("=" * 80)
        
        return self._success_response("\n".join(output))
    
    def _format_uri(self, uri):
        """格式化 URI 显示（提取号码部分）"""
        if not uri or uri == 'N/A':
            return 'N/A'
        
        # 去掉 sip: 前缀
        if uri.startswith('sip:'):
            uri = uri[4:]
        
        # 提取 @ 之前的部分
        if '@' in uri:
            uri = uri.split('@')[0]
        
        return uri[:18]  # 限制长度
    
    def _display_config(self, srv, params):
        """显示配置"""
        try:
            from config.config_manager import load_config
            config = load_config("config/config.json")
            
            output = [
                "=" * 60,
                "配置参数",
                "=" * 60,
            ]
            
            for key, value in config.items():
                output.append(f"{key:<30} : {value}")
            
            output.append("=" * 60)
            return self._success_response("\n".join(output))
        except Exception as e:
            return self._error_response(f"读取配置失败: {str(e)}")
    
    def _display_performance(self, srv, params):
        """显示性能指标"""
        output = [
            "=" * 60,
            "性能指标",
            "=" * 60,
        ]
        
        # 尝试获取性能指标（需要 psutil）
        try:
            import psutil
            output.extend([
                f"CPU 使用率     : {psutil.cpu_percent()}%",
                f"内存使用率     : {psutil.virtual_memory().percent}%",
                f"磁盘使用率     : {psutil.disk_usage('/').percent}%",
                f"网络连接数     : {len(psutil.net_connections())}",
            ])
        except ImportError:
            output.append("性能指标不可用 (需要安装 psutil)")
            output.append("")
            output.append("安装命令: pip install psutil")
        
        output.append("=" * 60)
        
        return self._success_response("\n".join(output))
    
    def _display_logs(self, params):
        """显示日志"""
        import os
        from datetime import datetime
        
        lines = int(params.get('LINES', 20))
        date = params.get('DATE', datetime.now().strftime('%Y-%m-%d'))
        
        # 日志文件路径（按日期分文件夹）
        log_file = f"logs/{date}/ims-sip-server.log"
        
        # 如果指定日期的日志不存在，尝试读取旧版本的日志文件
        if not os.path.exists(log_file):
            log_file = "logs/ims-sip-server.log"
        
        if not os.path.exists(log_file):
            return self._error_response(f"日志文件不存在: {log_file}")
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
                recent = log_lines[-lines:]
                
                output = [
                    "=" * 100,
                    f"日志文件: {log_file}",
                    f"最近 {len(recent)} 条日志",
                    "=" * 100,
                ]
                output.extend([line.rstrip() for line in recent])
                output.append("=" * 100)
                
                return self._success_response("\n".join(output))
        except Exception as e:
            return self._error_response(f"读取日志失败: {str(e)}")
    
    def _handle_set(self, parts):
        """处理 SET 命令"""
        if len(parts) < 2:
            return self._error_response("SET 命令需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "CFG":
            return self._set_config(params)
        elif obj == "LOG" or obj == "LOGLEVEL":
            return self._set_log_level(params)
        else:
            return self._error_response(f"不支持的 SET 对象: {obj}")
    
    def _set_config(self, params):
        """设置配置"""
        key = params.get('KEY')
        value = params.get('VALUE')
        
        if not key or not value:
            return self._error_response("需要指定 KEY 和 VALUE")
        
        try:
            from config.config_manager import apply_config_change
            success, message = apply_config_change(key, value)
            
            if success:
                return self._success_response(f"配置更新成功: {message}")
            else:
                return self._error_response(f"配置更新失败: {message}")
        except Exception as e:
            return self._error_response(f"设置配置失败: {str(e)}")
    
    def _set_log_level(self, params):
        """设置日志级别"""
        level = params.get('LEVEL', params.get('LOGLEVEL'))
        
        if not level:
            return self._error_response("需要指定 LEVEL")
        
        try:
            from config.config_manager import apply_config_change
            success, message = apply_config_change("LOG_LEVEL", level)
            
            if success:
                return self._success_response(f"日志级别已更新: {level}")
            else:
                return self._error_response(f"更新失败: {message}")
        except Exception as e:
            return self._error_response(f"设置日志级别失败: {str(e)}")
    
    def _handle_add(self, parts):
        """处理 ADD 命令"""
        if len(parts) < 2:
            return self._error_response("ADD 命令格式错误，需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "USR" or obj == "USER":
            return self._add_user(params)
        else:
            return self._error_response(f"不支持的对象类型: {obj}")
    
    def _handle_remove(self, parts):
        """处理 RMV 命令"""
        if len(parts) < 2:
            return self._error_response("RMV 命令格式错误，需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "USR" or obj == "USER":
            return self._remove_user(params)
        elif obj == "REG":
            return self._remove_registration(params)
        else:
            return self._error_response(f"不支持的对象类型: {obj}")
    
    def _handle_modify(self, parts):
        """处理 MOD 命令"""
        if len(parts) < 2:
            return self._error_response("MOD 命令格式错误，需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "USR" or obj == "USER":
            return self._modify_user(params)
        else:
            return self._error_response(f"不支持的对象类型: {obj}")
    
    def _add_user(self, params):
        """添加用户"""
        from sipcore.user_manager import get_user_manager
        
        username = params.get('USERNAME', '')
        password = params.get('PASSWORD', '')
        
        if not username:
            return self._error_response("缺少必需参数: USERNAME")
        if not password:
            return self._error_response("缺少必需参数: PASSWORD")
        
        user_mgr = get_user_manager()
        result = user_mgr.add_user(
            username=username,
            password=password,
            display_name=params.get('NAME', ''),
            phone=params.get('PHONE', ''),
            email=params.get('EMAIL', ''),
            service_type=params.get('SERVICE', 'BASIC')
        )
        
        if result['success']:
            user = result['user']
            output = [
                "=" * 60,
                "用户添加成功",
                "=" * 60,
                f"用户名        : {user.get('username')}",
                f"显示名称      : {user.get('display_name')}",
                f"电话号码      : {user.get('phone')}",
                f"邮箱          : {user.get('email')}",
                f"服务类型      : {user.get('service_type')}",
                f"状态          : {user.get('status')}",
                "=" * 60,
            ]
            return self._success_response("\n".join(output))
        else:
            return self._error_response(result['message'])
    
    def _remove_user(self, params):
        """删除用户"""
        from sipcore.user_manager import get_user_manager
        
        username = params.get('USERNAME', '')
        
        if not username:
            return self._error_response("缺少必需参数: USERNAME")
        
        user_mgr = get_user_manager()
        result = user_mgr.delete_user(username)
        
        if result['success']:
            return self._success_response(f"用户 {username} 删除成功")
        else:
            return self._error_response(result['message'])
    
    def _remove_registration(self, params):
        """强制注销指定用户"""
        uri = params.get('URI', '').strip()
        confirm = params.get('CONFIRM', '').upper()
        
        if not uri:
            return self._error_response("缺少必需参数: URI")
        
        if confirm != 'YES':
            return self._error_response("需要确认参数: CONFIRM=YES")
        
        registrations = self.server_globals.get('REGISTRATIONS', {})
        
        # 查找匹配的 AOR
        if '@' not in uri and not uri.startswith('sip:'):
            # 尝试匹配包含该号码的任意 AOR
            matched_aors = [aor for aor in registrations.keys() if uri in aor]
        else:
            # 精确匹配
            matched_aors = [aor for aor in registrations.keys() if aor == uri or aor == f"sip:{uri}"]
        
        if not matched_aors:
            return self._error_response(f"未找到 URI '{uri}' 的注册信息")
        
        # 删除所有匹配的注册
        removed_count = 0
        for aor in matched_aors:
            if aor in registrations:
                bindings_count = len(registrations[aor])
                del registrations[aor]
                removed_count += bindings_count
        
        return self._success_response(f"已强制注销 {len(matched_aors)} 个 AOR，共 {removed_count} 条注册记录")
    
    def _clear_registrations(self, params):
        """清除所有注册"""
        confirm = params.get('CONFIRM', '').upper()
        
        if confirm != 'YES':
            return self._error_response("需要确认参数: CONFIRM=YES")
        
        registrations = self.server_globals.get('REGISTRATIONS', {})
        
        # 统计注册数量
        total_aors = len(registrations)
        total_bindings = sum(len(bindings) for bindings in registrations.values())
        
        # 清空所有注册
        registrations.clear()
        
        return self._success_response(f"已清除所有注册：{total_aors} 个 AOR，共 {total_bindings} 条注册记录")
    
    def _export_cdr(self, params):
        """导出 CDR"""
        import os
        import shutil
        from datetime import datetime
        
        date = params.get('DATE', datetime.now().strftime('%Y-%m-%d'))
        if date == 'TODAY':
            date = datetime.now().strftime('%Y-%m-%d')
        
        record_type = params.get('TYPE', '').upper()
        format_type = params.get('FORMAT', 'CSV').upper()
        
        if format_type != 'CSV':
            return self._error_response("目前只支持 CSV 格式导出")
        
        cdr_file = f"CDR/{date}/cdr_{date}.csv"
        
        if not os.path.exists(cdr_file):
            return self._error_response(f"CDR 文件不存在: {cdr_file}")
        
        try:
            # 创建导出目录
            export_dir = "CDR/exports"
            os.makedirs(export_dir, exist_ok=True)
            
            # 导出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_filename = f"cdr_export_{date}_{timestamp}.csv"
            if record_type:
                export_filename = f"cdr_export_{date}_{record_type}_{timestamp}.csv"
            
            export_path = os.path.join(export_dir, export_filename)
            
            # 如果有类型过滤，需要过滤后导出
            if record_type:
                import csv
                with open(cdr_file, 'r', encoding='utf-8') as fin:
                    reader = csv.DictReader(fin)
                    fieldnames = reader.fieldnames
                    
                    with open(export_path, 'w', encoding='utf-8', newline='') as fout:
                        writer = csv.DictWriter(fout, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        count = 0
                        for row in reader:
                            if row.get('record_type', '') == record_type:
                                writer.writerow(row)
                                count += 1
                
                return self._success_response(
                    f"CDR 导出成功\n"
                    f"文件路径: {export_path}\n"
                    f"记录数量: {count} 条 (类型: {record_type})"
                )
            else:
                # 直接复制整个文件
                shutil.copy2(cdr_file, export_path)
                
                # 统计行数
                with open(export_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f) - 1  # 减去表头
                
                return self._success_response(
                    f"CDR 导出成功\n"
                    f"文件路径: {export_path}\n"
                    f"记录数量: {line_count} 条"
                )
        
        except Exception as e:
            import traceback
            return self._error_response(f"导出 CDR 失败: {str(e)}\n{traceback.format_exc()}")
    
    def _clear_cdr(self, params):
        """清理旧 CDR"""
        import os
        import shutil
        from datetime import datetime, timedelta
        
        before_date = params.get('BEFORE', '').strip()
        confirm = params.get('CONFIRM', '').upper()
        
        if not before_date:
            return self._error_response("缺少必需参数: BEFORE (格式: YYYY-MM-DD)")
        
        if confirm != 'YES':
            return self._error_response("需要确认参数: CONFIRM=YES")
        
        try:
            # 解析日期
            cutoff_date = datetime.strptime(before_date, '%Y-%m-%d')
        except ValueError:
            return self._error_response("日期格式错误，应为: YYYY-MM-DD")
        
        # 安全检查：不允许清理最近 7 天的数据
        min_date = datetime.now() - timedelta(days=7)
        if cutoff_date > min_date:
            return self._error_response(f"安全限制：不允许清理 {min_date.strftime('%Y-%m-%d')} 之后的数据")
        
        cdr_base_dir = "CDR"
        if not os.path.exists(cdr_base_dir):
            return self._error_response("CDR 目录不存在")
        
        try:
            deleted_dirs = []
            deleted_files = 0
            
            # 遍历 CDR 目录
            for dirname in os.listdir(cdr_base_dir):
                dir_path = os.path.join(cdr_base_dir, dirname)
                
                # 跳过非目录和 exports 目录
                if not os.path.isdir(dir_path) or dirname == 'exports':
                    continue
                
                # 尝试解析目录名为日期
                try:
                    dir_date = datetime.strptime(dirname, '%Y-%m-%d')
                    
                    # 如果早于截止日期，删除
                    if dir_date < cutoff_date:
                        # 统计文件数
                        file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                        deleted_files += file_count
                        
                        # 删除目录
                        shutil.rmtree(dir_path)
                        deleted_dirs.append(dirname)
                except ValueError:
                    # 目录名不是日期格式，跳过
                    continue
            
            if deleted_dirs:
                return self._success_response(
                    f"已清理 CDR 数据\n"
                    f"删除目录数: {len(deleted_dirs)} 个\n"
                    f"删除文件数: {deleted_files} 个\n"
                    f"删除日期: {', '.join(sorted(deleted_dirs)[:10])}" + 
                    (f" ..." if len(deleted_dirs) > 10 else "")
                )
            else:
                return self._success_response(f"没有找到 {before_date} 之前的 CDR 数据")
        
        except Exception as e:
            import traceback
            return self._error_response(f"清理 CDR 失败: {str(e)}\n{traceback.format_exc()}")
    
    def _modify_user(self, params):
        """修改用户信息"""
        from sipcore.user_manager import get_user_manager
        
        username = params.get('USERNAME', '')
        
        if not username:
            return self._error_response("缺少必需参数: USERNAME")
        
        # 收集要修改的字段
        updates = {}
        if 'PASSWORD' in params:
            updates['password'] = params['PASSWORD']
        if 'NAME' in params:
            updates['display_name'] = params['NAME']
        if 'PHONE' in params:
            updates['phone'] = params['PHONE']
        if 'EMAIL' in params:
            updates['email'] = params['EMAIL']
        if 'SERVICE' in params:
            updates['service_type'] = params['SERVICE']
        if 'STATUS' in params:
            updates['status'] = params['STATUS']
        
        if not updates:
            return self._error_response("没有指定要修改的字段")
        
        user_mgr = get_user_manager()
        result = user_mgr.modify_user(username, **updates)
        
        if result['success']:
            user = result['user']
            output = [
                "=" * 60,
                "用户修改成功",
                "=" * 60,
                f"用户名        : {user.get('username')}",
                f"显示名称      : {user.get('display_name')}",
                f"电话号码      : {user.get('phone')}",
                f"邮箱          : {user.get('email')}",
                f"服务类型      : {user.get('service_type')}",
                f"状态          : {user.get('status')}",
                f"更新时间      : {user.get('update_time')}",
                "=" * 60,
            ]
            return self._success_response("\n".join(output))
        else:
            return self._error_response(result['message'])
    
    def _handle_clear(self, parts):
        """处理 CLR 命令"""
        if len(parts) < 2:
            return self._error_response("CLR 命令格式错误，需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "REG":
            return self._clear_registrations(params)
        elif obj == "CDR":
            return self._clear_cdr(params)
        else:
            return self._error_response(f"不支持的对象类型: {obj}")
    
    def _handle_reset(self, parts):
        """处理 RST 命令"""
        return self._error_response("RST 命令暂未实现")
    
    def _handle_export(self, parts):
        """处理 EXP 命令"""
        if len(parts) < 2:
            return self._error_response("EXP 命令格式错误，需要指定对象")
        
        obj = parts[1].upper()
        params = self._parse_params(parts[2:])
        
        if obj == "CDR":
            return self._export_cdr(params)
        else:
            return self._error_response(f"不支持的对象类型: {obj}")
    
    def _handle_save(self, parts):
        """处理 SAVE 命令"""
        try:
            from config.config_manager import save_config, load_config
            config = load_config("config/config.json")
            save_config("config/config.json", config)
            return self._success_response("配置已保存")
        except Exception as e:
            return self._error_response(f"保存配置失败: {str(e)}")
    
    def _handle_help(self, parts):
        """处理 HELP 命令"""
        tree = MMLCommandTree.get_command_tree()
        
        output = [
            "=" * 80,
            "MML 命令帮助",
            "=" * 80,
            "",
            "命令格式:",
            "  VERB OBJECT [PARAM1=VALUE1] [PARAM2=VALUE2] ...",
            "",
            "支持的命令动词:",
            "  DSP  - 显示/查询",
            "  ADD  - 添加",
            "  RMV  - 删除",
            "  MOD  - 修改",
            "  SET  - 设置",
            "  CLR  - 清除",
            "  RST  - 重置",
            "  EXP  - 导出",
            "  SAVE - 保存",
            "",
            "示例:",
            "  DSP SYSINFO                    - 显示系统信息",
            "  DSP REG ALL                    - 显示所有注册",
            "  SET LOG LEVEL=DEBUG            - 设置日志级别为 DEBUG",
            "  DSP CDR DATE=TODAY TYPE=CALL   - 显示今日呼叫 CDR",
            "",
            "=" * 80,
        ]
        
        return self._success_response("\n".join(output))
    
    def _success_response(self, message):
        """成功响应"""
        return {
            "retcode": 0,
            "retmsg": "Success",
            "output": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _error_response(self, message):
        """错误响应"""
        return {
            "retcode": 1,
            "retmsg": message,
            "output": f"ERROR: {message}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


class MMLHTTPHandler(BaseHTTPRequestHandler):
    """MML HTTP 请求处理器"""
    
    executor = None  # 将在 init_mml_interface 中设置
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self._serve_index()
        elif parsed_path.path == '/api/command_tree':
            self._serve_command_tree()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/execute':
            self._execute_command()
        else:
            self.send_error(404)
    
    def _serve_index(self):
        """提供主页面"""
        html_file = os.path.join(os.path.dirname(__file__), 'mml_interface.html')
        
        try:
            with open(html_file, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "Interface file not found")
    
    def _serve_command_tree(self):
        """提供命令树"""
        tree = MMLCommandTree.get_command_tree()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps(tree, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response)
    
    def _execute_command(self):
        """执行命令"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            command = data.get('command', '').strip()
            
            if not command:
                result = {
                    "retcode": 1,
                    "retmsg": "空命令",
                    "output": "ERROR: 命令不能为空"
                }
            else:
                result = self.executor.execute(command)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(result, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, str(e))


def init_mml_interface(port=8888, server_globals=None):
    """初始化 MML 管理界面
    
    Args:
        port: HTTP 端口
        server_globals: 服务器全局变量字典，包含 REGISTRATIONS, DIALOGS 等
    """
    # 创建执行器并传递服务器状态
    MMLHTTPHandler.executor = MMLCommandExecutor(server_globals)
    
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), MMLHTTPHandler)
            print(f"[MML] MML 管理界面已启动: http://0.0.0.0:{port}", flush=True)
            server.serve_forever()
        except Exception as e:
            print(f"[MML] ERROR: {e}", flush=True)
    
    # 在独立线程中运行 HTTP 服务器
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    # 启动 WebSocket 日志推送服务器（如果可用）
    if WEBSOCKET_AVAILABLE:
        ws_port = port + 1  # WebSocket 端口 = HTTP 端口 + 1
        start_websocket_server(ws_port)
        
        # 添加日志处理器，将日志推送到队列
        class WebSocketLogHandler(logging.Handler):
            """将日志推送到队列，由 WebSocket 服务器消费"""
            def emit(self, record):
                try:
                    log_message = self.format(record)
                    # 移除 ANSI 颜色代码（如 [32m, [0m 等）
                    log_message = re.sub(r'\x1b\[[0-9;]*m', '', log_message)
                    # 放入队列，如果队列满了就丢弃旧消息
                    try:
                        log_queue.put_nowait(log_message)
                    except queue.Full:
                        # 队列满了，丢弃最老的消息
                        try:
                            log_queue.get_nowait()
                            log_queue.put_nowait(log_message)
                        except:
                            pass
                except:
                    pass
        
        # 添加到根日志器
        ws_handler = WebSocketLogHandler()
        ws_handler.setLevel(logging.DEBUG)
        ws_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logging.getLogger().addHandler(ws_handler)


# WebSocket 日志推送（可选）
if WEBSOCKET_AVAILABLE:
    async def log_push_handler(websocket):
        """WebSocket 日志推送处理器"""
        log_subscribers.add(websocket)
        try:
            # 保持连接
            await websocket.wait_closed()
        finally:
            log_subscribers.discard(websocket)
    
    async def broadcast_logs():
        """从队列中读取日志并广播给所有客户端"""
        while True:
            try:
                # 非阻塞地检查队列
                await asyncio.sleep(0.1)
                
                # 批量获取所有待发送的日志
                messages = []
                while not log_queue.empty() and len(messages) < 100:
                    try:
                        messages.append(log_queue.get_nowait())
                    except queue.Empty:
                        break
                
                # 广播给所有订阅者
                if messages and log_subscribers:
                    for ws in list(log_subscribers):
                        try:
                            for msg in messages:
                                await ws.send(msg)
                        except:
                            # 连接已断开，移除订阅者
                            log_subscribers.discard(ws)
            except Exception as e:
                print(f"[MML] 日志广播错误: {e}")
                await asyncio.sleep(1)
    
    def start_websocket_server(port=8889):
        """启动 WebSocket 服务器"""
        async def main():
            async with websockets.serve(log_push_handler, "0.0.0.0", port):
                print(f"[MML] WebSocket 日志推送服务已启动: ws://0.0.0.0:{port}")
                # 启动日志广播任务
                asyncio.create_task(broadcast_logs())
                await asyncio.Future()  # 永久运行
        
        def run():
            asyncio.run(main())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()


if __name__ == "__main__":
    # 测试
    init_mml_interface(8888)
    
    if WEBSOCKET_AVAILABLE:
        start_websocket_server(8889)
    
    print("Press Ctrl+C to stop")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

