# sipcore/timers.py
"""
RFC 3261 SIP 定时器实现

主要定时器：
- Timer A: INVITE 请求重传 (T1)
- Timer B: INVITE 事务超时 (64*T1)
- Timer C: 代理 INVITE 事务超时 (> 3分钟)
- Timer D: 等待响应重传 (> 32秒)
- Timer E: 非 INVITE 请求重传 (T1)
- Timer F: 非 INVITE 事务超时 (64*T1)
- Timer G: INVITE 响应重传 (T1)
- Timer H: 等待 ACK (64*T1)
- Timer I: 等待 ACK 重传 (T4)
- Timer J: 等待重传的非 INVITE 请求 (64*T1)
- Timer K: 等待响应重传 (T4)

RFC 3261 推荐值：
- T1 = 500ms (RTT estimate)
- T2 = 4s (maximum retransmit interval)
- T4 = 5s (maximum duration a message will remain in the network)
"""

import asyncio
import time
from typing import Dict, Tuple, Callable
import logging

# RFC 3261 定时器常量 (单位：秒)
T1 = 0.5   # RTT estimate: 500ms
T2 = 4.0   # Maximum retransmit interval: 4s
T4 = 5.0   # Maximum duration message will remain in network: 5s

# 事务超时时间
TIMER_B = 64 * T1  # INVITE 事务超时: 32s
TIMER_F = 64 * T1  # 非 INVITE 事务超时: 32s
TIMER_H = 64 * T1  # 等待 ACK: 32s
TIMER_J = 64 * T1  # 等待重传: 32s

# 代理特定定时器
TIMER_C = 180.0    # 代理 INVITE 事务超时: 3分钟

# 应用层定时器
DIALOG_TIMEOUT = 3600.0      # 对话超时: 1小时
PENDING_CLEANUP = 300.0      # 待处理请求清理: 5分钟
BRANCH_CLEANUP = 60.0        # INVITE branch 清理: 1分钟
REGISTRATION_CHECK = 30.0    # 注册检查间隔: 30秒


class SIPTimers:
    """SIP 定时器管理器"""
    
    def __init__(self, log):
        self.log = log
        self._tasks = []
        self._running = False
        
    async def start(self, 
                   pending_requests: Dict,
                   dialogs: Dict,
                   invite_branches: Dict,
                   reg_bindings: Dict):
        """
        启动所有定时器
        
        Args:
            pending_requests: PENDING_REQUESTS 字典引用
            dialogs: DIALOGS 字典引用
            invite_branches: INVITE_BRANCHES 字典引用
            reg_bindings: REG_BINDINGS 字典引用
        """
        self._running = True
        
        # 启动各个定时器任务
        self._tasks.append(asyncio.create_task(
            self._cleanup_pending_requests(pending_requests)
        ))
        self._tasks.append(asyncio.create_task(
            self._cleanup_dialogs(dialogs)
        ))
        self._tasks.append(asyncio.create_task(
            self._cleanup_invite_branches(invite_branches)
        ))
        self._tasks.append(asyncio.create_task(
            self._cleanup_expired_registrations(reg_bindings)
        ))
        
        self.log.info("[TIMERS] Started all SIP timers")
        
    async def stop(self):
        """停止所有定时器"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self.log.info("[TIMERS] Stopped all SIP timers")
    
    async def _cleanup_pending_requests(self, pending_requests: Dict):
        """
        清理超时的待处理请求
        
        RFC 3261 Timer F: 非 INVITE 事务在 64*T1 (32秒) 后超时
        """
        cleanup_interval = PENDING_CLEANUP
        request_timestamps: Dict[str, float] = {}
        
        while self._running:
            try:
                await asyncio.sleep(cleanup_interval)
                
                now = time.time()
                expired_calls = []
                
                # 检查所有待处理请求
                for call_id in list(pending_requests.keys()):
                    # 记录首次见到的时间
                    if call_id not in request_timestamps:
                        request_timestamps[call_id] = now
                        continue
                    
                    # 检查是否超时
                    age = now - request_timestamps[call_id]
                    if age > PENDING_CLEANUP:
                        expired_calls.append(call_id)
                
                # 清理超时的请求
                for call_id in expired_calls:
                    addr = pending_requests.pop(call_id, None)
                    request_timestamps.pop(call_id, None)
                    if addr:
                        self.log.info(f"[TIMER-F] Cleaned up expired pending request: {call_id} (age: {age:.1f}s)")
                
                # 清理不再存在的时间戳
                for call_id in list(request_timestamps.keys()):
                    if call_id not in pending_requests:
                        request_timestamps.pop(call_id, None)
                
                if expired_calls:
                    self.log.debug(f"[TIMER-CLEANUP] Pending requests: {len(pending_requests)}, Cleaned: {len(expired_calls)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.error(f"[TIMER-F] Error in pending requests cleanup: {e}")
    
    async def _cleanup_dialogs(self, dialogs: Dict):
        """
        清理长时间未活动的对话
        
        应用层定时器：防止对话泄漏
        """
        dialog_timestamps: Dict[str, float] = {}
        
        while self._running:
            try:
                await asyncio.sleep(60.0)  # 每分钟检查一次
                
                now = time.time()
                expired_dialogs = []
                
                for call_id in list(dialogs.keys()):
                    # 记录首次见到的时间
                    if call_id not in dialog_timestamps:
                        dialog_timestamps[call_id] = now
                        continue
                    
                    # 检查是否超时（1小时无活动）
                    age = now - dialog_timestamps[call_id]
                    if age > DIALOG_TIMEOUT:
                        expired_dialogs.append(call_id)
                
                # 清理超时的对话
                for call_id in expired_dialogs:
                    dialog_info = dialogs.pop(call_id, None)
                    dialog_timestamps.pop(call_id, None)
                    if dialog_info:
                        self.log.warning(f"[TIMER-DIALOG] Cleaned up stale dialog: {call_id} (age: {age/60:.1f}min)")
                
                # 清理不再存在的时间戳
                for call_id in list(dialog_timestamps.keys()):
                    if call_id not in dialogs:
                        dialog_timestamps.pop(call_id, None)
                
                if expired_dialogs:
                    self.log.info(f"[TIMER-CLEANUP] Dialogs: {len(dialogs)}, Cleaned: {len(expired_dialogs)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.error(f"[TIMER-DIALOG] Error in dialog cleanup: {e}")
    
    async def _cleanup_invite_branches(self, invite_branches: Dict):
        """
        清理 INVITE branch 映射
        
        RFC 3261 Timer H: 等待 ACK 超时后清理
        CANCEL 必须在 INVITE 响应后的合理时间内到达
        """
        branch_timestamps: Dict[str, float] = {}
        
        while self._running:
            try:
                await asyncio.sleep(BRANCH_CLEANUP)
                
                now = time.time()
                expired_branches = []
                
                for call_id in list(invite_branches.keys()):
                    # 记录首次见到的时间
                    if call_id not in branch_timestamps:
                        branch_timestamps[call_id] = now
                        continue
                    
                    # 检查是否超时（64*T1 = 32秒）
                    age = now - branch_timestamps[call_id]
                    if age > TIMER_H:
                        expired_branches.append(call_id)
                
                # 清理超时的 branch
                for call_id in expired_branches:
                    branch = invite_branches.pop(call_id, None)
                    branch_timestamps.pop(call_id, None)
                    if branch:
                        self.log.debug(f"[TIMER-H] Cleaned up INVITE branch: {call_id} (branch: {branch}, age: {age:.1f}s)")
                
                # 清理不再存在的时间戳
                for call_id in list(branch_timestamps.keys()):
                    if call_id not in invite_branches:
                        branch_timestamps.pop(call_id, None)
                
                if expired_branches:
                    self.log.debug(f"[TIMER-CLEANUP] INVITE branches: {len(invite_branches)}, Cleaned: {len(expired_branches)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.error(f"[TIMER-H] Error in INVITE branch cleanup: {e}")
    
    async def _cleanup_expired_registrations(self, reg_bindings: Dict):
        """
        清理过期的注册绑定
        
        RFC 3261: Contact 绑定在 expires 时间后自动失效
        """
        while self._running:
            try:
                await asyncio.sleep(REGISTRATION_CHECK)
                
                now = int(time.time())
                total_expired = 0
                
                for aor in list(reg_bindings.keys()):
                    bindings = reg_bindings[aor]
                    original_count = len(bindings)
                    
                    # 过滤掉已过期的绑定
                    reg_bindings[aor] = [b for b in bindings if b["expires"] > now]
                    
                    expired_count = original_count - len(reg_bindings[aor])
                    total_expired += expired_count
                    
                    if expired_count > 0:
                        self.log.info(f"[TIMER-REG] Cleaned up {expired_count} expired binding(s) for {aor}")
                    
                    # 如果 AOR 没有绑定了，删除这个 AOR
                    if not reg_bindings[aor]:
                        del reg_bindings[aor]
                        self.log.debug(f"[TIMER-REG] Removed AOR {aor} (no bindings left)")
                
                if total_expired > 0:
                    self.log.info(f"[TIMER-CLEANUP] Total expired registrations: {total_expired}, Active AORs: {len(reg_bindings)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.error(f"[TIMER-REG] Error in registration cleanup: {e}")


def create_timers(log) -> SIPTimers:
    """创建 SIP 定时器管理器"""
    return SIPTimers(log)

