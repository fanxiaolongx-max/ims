# SIP 核心实现文档

本文档详细说明 IMS SIP Server 的 SIP 协议核心实现。

---

## 📋 目录

1. [架构概览](#架构概览)
2. [SIP 方法支持](#sip-方法支持)
3. [路由机制](#路由机制)
4. [对话管理](#对话管理)
5. [定时器机制](#定时器机制)
6. [NAT 处理](#nat-处理)
7. [RFC 3261 合规性](#rfc-3261-合规性)

---

## 🏗️ 架构概览

### 核心模块

```
sipcore/
├── parser.py           # SIP 消息解析器
├── transport_udp.py    # UDP 传输层
├── logger.py           # 日志系统
├── cdr.py             # CDR 话单系统
└── timers.py          # RFC 3261 定时器
```

### 数据结构

#### REGISTRATIONS
存储用户注册信息：
```python
REGISTRATIONS = {
    "sip:1001@192.168.1.1": [
        {
            "contact": "sip:1001@192.168.1.100:5060",
            "expires": 3600,
            "registered_at": 1698400000.0
        }
    ]
}
```

#### DIALOGS
存储对话状态（呼叫中）：
```python
DIALOGS = {
    "abc123-callid": {
        "caller_addr": ("192.168.1.100", 5060),
        "callee_addr": ("192.168.1.200", 5060),
        "created_at": 1698400000.0
    }
}
```

#### PENDING_REQUESTS
存储待处理请求的发送者地址：
```python
PENDING_REQUESTS = {
    "xyz789-callid": ("192.168.1.100", 5060)
}
```

#### INVITE_BRANCHES
存储 INVITE 的 Via branch，用于 CANCEL 匹配：
```python
INVITE_BRANCHES = {
    "abc123-callid": "z9hG4bK-1234567890"
}
```

---

## 📞 SIP 方法支持

### REGISTER - 用户注册

**处理流程：**
1. 解析 Contact 头获取用户地址
2. 修正 NAT 地址（如果需要）
3. 存储到 REGISTRATIONS
4. 返回 200 OK 带所有绑定

**认证流程：**
```
UA -> REGISTER (无认证)
<- 401 Unauthorized (Challenge)
UA -> REGISTER (带 Authorization)
<- 200 OK
```

**CDR 记录：**
- 注册成功：`REGISTER` 类型
- 注销：`UNREGISTER` 类型
- 相同 Call-ID 的注册会自动合并

**关键代码：**
```python
def handle_register(msg, addr, transport):
    # 1. 提取用户信息
    aor = extract_aor(msg.get("to"))
    
    # 2. 处理 Contact
    contact = msg.get("contact")
    expires = int(msg.get("expires", "3600"))
    
    # 3. NAT 修正
    if FORCE_LOCAL_ADDR or addr[0] not in LOCAL_NETWORKS:
        contact = fix_contact_address(contact, addr)
    
    # 4. 存储注册
    if expires > 0:
        REGISTRATIONS[aor].append({
            "contact": contact,
            "expires": expires,
            "registered_at": time.time()
        })
    else:
        # 注销
        REGISTRATIONS[aor] = []
    
    # 5. 返回 200 OK
    return make_response(msg, 200, "OK")
```

---

### INVITE - 呼叫建立

**处理流程：**
1. 查找目标用户的注册地址
2. 改写 Request-URI
3. 添加 Record-Route 头
4. 记录到 DIALOGS
5. 转发给被叫

**Record-Route 处理：**
```python
# 添加 Record-Route（代理修改了 R-URI 时必须添加）
if modified_ruri:
    msg.add_header("Record-Route", f"<sip:{SERVER_IP}:{SERVER_PORT};lr>")
```

**CDR 记录：**
- `CALL_START` - 记录发起时间和双方信息

**状态机：**
```
INITIAL -> EARLY -> CONFIRMED -> TERMINATED
   |         |          |            |
 INVITE   180/183     200 OK        BYE
```

---

### ACK - 确认

**两种类型的 ACK：**

#### 2xx ACK（正常流程）
- 使用 Route 头路由
- 直接转发，不修改
- 不添加 Via 头（无状态代理模式）

#### 非 2xx ACK（失败流程）
- R-URI 与原始 INVITE 相同
- Via branch 与原始 INVITE 相同
- 用于终止失败的 INVITE 事务

**关键逻辑：**
```python
def _is_2xx_ack(msg):
    """判断是否为 2xx ACK"""
    call_id = msg.get("call-id")
    
    # 如果在 DIALOGS 中，说明呼叫已建立（收到过 200 OK）
    return call_id in DIALOGS
```

---

### BYE - 呼叫终止

**处理流程：**
1. 从 DIALOGS 查找对端地址
2. 使用 Route 头路由（in-dialog 请求）
3. 转发给对端
4. 清理 DIALOGS

**CDR 记录：**
- `CALL_END` - 记录挂断时间和原因

**防重复：**
```python
# 只在第一次收到 BYE 时记录 CDR
if call_id in DIALOGS:
    cdr.record_call_end(call_id=call_id, ...)
    # 转发后清理
```

**错误处理：**
```python
# 网络不可达时
except OSError as e:
    if e.errno == 65:  # No route to host
        return make_response(msg, 408, "Request Timeout")
```

---

### CANCEL - 取消呼叫

**处理流程：**
1. 查找对应的 INVITE 事务
2. 复用 INVITE 的 Via branch
3. 改写 R-URI（与 INVITE 相同）
4. 转发给被叫

**Via Branch 复用：**
```python
# 记录 INVITE 的 branch
if method == "INVITE":
    branch = extract_via_branch(msg)
    INVITE_BRANCHES[call_id] = branch

# CANCEL 时复用
if method == "CANCEL":
    branch = INVITE_BRANCHES.get(call_id)
    if branch:
        msg.set_via_branch(branch)
```

**CDR 记录：**
- `CALL_CANCEL` - 记录取消原因

---

### MESSAGE - 即时消息

**处理流程：**
1. 查找目标用户地址（与 INVITE 相同）
2. 改写 R-URI
3. 转发给接收方
4. 转发 200 OK 给发送方

**CDR 记录：**
- `MESSAGE` - 记录短信内容和双方信息
- 使用 `Call-ID + CSeq` 作为唯一标识

**关键代码：**
```python
# MESSAGE 与 INVITE 使用相同的路由逻辑
if method in ("INVITE", "MESSAGE") and _is_initial_request(msg):
    target_uri = msg.request_uri
    target_contact = lookup_registration(target_uri)
    if target_contact:
        msg.request_uri = target_contact
```

---

### OPTIONS - 能力查询

**处理流程：**
1. 如果目标是服务器本身，直接返回 200 OK
2. 否则转发给目标用户
3. 返回支持的方法列表

**响应示例：**
```
SIP/2.0 200 OK
Allow: INVITE, ACK, BYE, CANCEL, OPTIONS, MESSAGE, REGISTER
Supported: path, gruu
Accept: application/sdp
```

**CDR 记录：**
- OPTIONS 请求会记录，但不创建 DIALOG

---

## 🧭 路由机制

### 初始请求路由

**判断条件：**
```python
def _is_initial_request(msg):
    """没有 To tag = 初始请求"""
    to_header = msg.get("to")
    return ";tag=" not in to_header
```

**路由逻辑：**
1. 提取 Request-URI 中的 AOR
2. 查找 REGISTRATIONS
3. 改写 R-URI 为注册的 Contact
4. 添加 Record-Route
5. 转发

**示例：**
```
原始: INVITE sip:1002@server.com SIP/2.0
改写: INVITE sip:1002@192.168.1.200:5060 SIP/2.0
添加: Record-Route: <sip:server.com;lr>
```

---

### In-Dialog 请求路由

**判断条件：**
- To 头包含 tag
- 或 Route 头存在

**路由逻辑：**
1. 检查 Route 头
2. 如果第一个 Route 是服务器自己，弹出它
3. 使用剩余的 Route 头路由
4. 如果没有 Route 头，使用 Request-URI

**示例：**
```
BYE sip:1002@192.168.1.200:5060 SIP/2.0
Route: <sip:server.com;lr>, <sip:192.168.1.200:5060>

处理后:
BYE sip:1002@192.168.1.200:5060 SIP/2.0
Route: <sip:192.168.1.200:5060>
```

---

### 响应路由

**Via 头处理：**
1. 解析顶层 Via 头
2. 检查 received 和 rport 参数（NAT 修正）
3. 提取目标地址和端口
4. 弹出顶层 Via
5. 转发

**示例：**
```
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK123;received=1.2.3.4;rport=5060
Via: SIP/2.0/UDP 192.168.1.1:5060;branch=z9hG4bK456

响应发往: 1.2.3.4:5060 (使用 received 和 rport)
弹出后只剩: Via: SIP/2.0/UDP 192.168.1.1:5060;branch=z9hG4bK456
```

**特殊处理：**
- INVITE 的最终响应（2xx, 4xx, 5xx, 6xx）使用 DIALOGS 路由
- 其他方法的响应使用 Via 头路由

---

### 环路检测

**检测方法：**
1. 检查 Via 头栈中是否有服务器自己的地址
2. 检查 Max-Forwards 是否为 0
3. 检查 R-URI 是否指向服务器自己

**处理：**
```python
# Via 头环路检测
if _via_contains_self(msg):
    log.drop("Loop detected in Via")
    return

# Max-Forwards 检测
max_forwards = int(msg.get("max-forwards", "70"))
if max_forwards <= 0:
    return make_response(msg, 483, "Too Many Hops")

# 递减 Max-Forwards
msg.set_header("max-forwards", str(max_forwards - 1))
```

---

## 💾 对话管理

### DIALOGS 生命周期

```
创建: 收到 INVITE 时
状态: {caller_addr, callee_addr, created_at}
更新: 收到 200 OK 时（如果需要）
清理: 收到 BYE 时 或 超时（1小时）
```

### PENDING_REQUESTS 生命周期

```
创建: 转发请求时
状态: 请求发送者地址
用途: 响应路由（找到原始请求者）
清理: 收到最终响应时 或 超时（5分钟）
```

### 清理机制

**定时器触发：**
- `DIALOG_TIMEOUT`: 1小时未活动
- `PENDING_CLEANUP`: 5分钟无响应
- `BRANCH_CLEANUP`: 60秒清理 INVITE branch

**手动清理：**
```python
# BYE 收到 200 OK 后
if call_id in DIALOGS:
    del DIALOGS[call_id]

# 事务完成后
if call_id in PENDING_REQUESTS:
    del PENDING_REQUESTS[call_id]
```

---

## ⏱️ 定时器机制

### RFC 3261 标准定时器

| 定时器 | 值 | 用途 |
|--------|---|------|
| **T1** | 500ms | RTT 估算 |
| **T2** | 4s | 最大重传间隔 |
| **T4** | 5s | 最大消息存活时间 |
| **Timer A** | T1 | INVITE 重传（初始） |
| **Timer B** | 64*T1 | INVITE 事务超时 |
| **Timer D** | 32s | 响应重传吸收 |
| **Timer F** | 64*T1 | 非 INVITE 事务超时 |
| **Timer H** | 64*T1 | 等待 ACK 超时 |

### 应用层定时器

| 定时器 | 值 | 用途 |
|--------|---|------|
| **DIALOG_TIMEOUT** | 3600s | 对话超时清理 |
| **PENDING_CLEANUP** | 300s | 待处理请求清理 |
| **BRANCH_CLEANUP** | 60s | INVITE branch 清理 |
| **REGISTRATION_CHECK** | 30s | 注册过期检查 |

### 定时器实现

```python
async def cleanup_timer():
    """后台清理任务"""
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        
        # 清理过期对话
        now = time.time()
        for call_id, dialog in list(DIALOGS.items()):
            if now - dialog["created_at"] > DIALOG_TIMEOUT:
                del DIALOGS[call_id]
                log.debug(f"[TIMER-DIALOG] Cleaned: {call_id}")
        
        # 清理待处理请求
        for call_id, info in list(PENDING_REQUESTS.items()):
            if now - info["created_at"] > PENDING_CLEANUP:
                del PENDING_REQUESTS[call_id]
                log.debug(f"[TIMER-F] Cleaned: {call_id}")
```

---

## 🌐 NAT 处理

### NAT 检测

```python
def _needs_nat_fix(addr):
    """判断是否需要 NAT 修正"""
    if FORCE_LOCAL_ADDR:
        return True
    
    # 检查是否在本地网络
    return addr[0] not in LOCAL_NETWORKS
```

### Contact 修正

```python
def fix_contact_address(contact, real_addr):
    """修正 Contact 头的地址和端口"""
    # 提取用户部分
    user = extract_user(contact)
    
    # 重写为真实地址
    return f"sip:{user}@{real_addr[0]}:{real_addr[1]}"
```

### Via 参数处理

**received 参数：**
- 记录消息的真实来源 IP
- 用于响应路由

**rport 参数：**
- 记录消息的真实来源端口
- 用于响应路由

**示例：**
```python
# 请求到达时添加
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK123
# 添加后
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK123;received=1.2.3.4;rport=5060
```

### 网络模式

#### 本机测试模式
```python
SERVER_IP = "127.0.0.1"
FORCE_LOCAL_ADDR = True
```
- 所有地址强制转换为 127.0.0.1
- 适合开发测试

#### 局域网模式
```python
SERVER_IP = "192.168.1.1"
FORCE_LOCAL_ADDR = False
LOCAL_NETWORKS = ["192.168.1.0/24"]
```
- 保持原始地址
- 适合生产环境

---

## ✅ RFC 3261 合规性

### 代理行为

| 要求 | 实现 | 说明 |
|-----|-----|------|
| **Via 头处理** | ✅ | 请求添加 Via，响应弹出 Via |
| **Max-Forwards** | ✅ | 转发时递减，0 时返回 483 |
| **Record-Route** | ✅ | 修改 R-URI 时添加 |
| **Route 头处理** | ✅ | 弹出指向自己的 Route |
| **环路检测** | ✅ | Via 栈检查 + Max-Forwards |
| **无状态 ACK** | ✅ | ACK 不添加 Via |
| **Contact 修正** | ✅ | NAT 环境修正 Contact |

### ACK 处理

| 类型 | R-URI | Route | Via | 说明 |
|-----|-------|-------|-----|------|
| **2xx ACK** | From Route | 保留 | 不添加 | 正常流程 |
| **非 2xx ACK** | 与 INVITE 相同 | 清空 | 不添加 | 错误流程 |

### 事务处理

| 方法 | 类型 | 超时 | 重传 |
|-----|-----|------|------|
| **INVITE** | Client Transaction | 64*T1 (32s) | 指数退避 |
| **非 INVITE** | Client Transaction | 64*T1 (32s) | Timer F |
| **ACK** | 无事务 | - | 不重传 |

### 响应代码

| 代码 | 说明 | 使用场景 |
|-----|------|---------|
| **100** | Trying | INVITE 收到 |
| **180** | Ringing | 被叫振铃 |
| **200** | OK | 成功 |
| **401** | Unauthorized | 需要认证 |
| **404** | Not Found | 用户未注册 |
| **480** | Temporarily Unavailable | 网络不可达 |
| **481** | Call/Transaction Does Not Exist | 对话不存在 |
| **482** | Loop Detected | 环路检测 |
| **483** | Too Many Hops | Max-Forwards = 0 |
| **486** | Busy Here | 被叫忙 |
| **487** | Request Terminated | CANCEL 导致 |
| **503** | Service Unavailable | 服务不可用 |

---

## 🔍 调试技巧

### 启用详细日志

```python
# 设置日志级别为 DEBUG
LOG_LEVEL = "DEBUG"
```

### 关键日志标记

```bash
# 查看路由决策
grep "\[FWD\]" ims-sip-server.log

# 查看对话状态
grep "\[DIALOG\]" ims-sip-server.log

# 查看 ACK 处理
grep "ACK" ims-sip-server.log

# 查看定时器清理
grep "\[TIMER" ims-sip-server.log

# 查看 CDR 记录
grep "\[CDR\]" ims-sip-server.log
```

### 消息流跟踪

```python
# RX: 收到消息
[RX] 192.168.1.100:5060 -> INVITE sip:1002@server.com

# FWD: 转发消息
[FWD] INVITE -> 192.168.1.200:5060 (R-URI modified)

# TX: 发送消息
[TX] 192.168.1.100:5060 <- SIP/2.0 100 Trying

# DROP: 丢弃消息
[DROP] Loop detected: skipping self-forward
```

---

## 📊 性能优化

### 异步 I/O

```python
# 使用 asyncio UDP 传输
class SIPProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        # 非阻塞处理
        asyncio.create_task(handle_message(data, addr))
```

### 内存管理

- 定时清理过期状态
- 限制 REGISTRATIONS 数量
- 限制 DIALOGS 数量
- 限制 CDR 缓存大小

### 性能监控

```python
# 记录处理时间
start = time.time()
handle_message(msg)
duration = time.time() - start
log.debug(f"Processing time: {duration:.3f}s")
```

---

## 🎯 最佳实践

### 开发环境
- 使用 DEBUG 日志级别
- 启用 FORCE_LOCAL_ADDR
- 使用单机多 UA 测试

### 生产环境
- 使用 INFO 或 WARNING 日志级别
- 禁用 FORCE_LOCAL_ADDR
- 配置正确的 LOCAL_NETWORKS
- 定期备份 CDR 数据
- 监控内存和 CPU 使用

### 故障排查
1. 检查日志文件
2. 验证网络连通性
3. 确认防火墙规则
4. 检查 NAT 配置
5. 使用抓包工具（Wireshark）

---

## 📚 参考文档

- **RFC 3261**: SIP - Session Initiation Protocol
- **RFC 3263**: Locating SIP Servers
- **RFC 3265**: SIP-Specific Event Notification
- **RFC 3581**: Symmetric Response Routing
- **RFC 6026**: Correct Transaction Handling for 2xx Responses

---

**最后更新**: 2025-10-27

