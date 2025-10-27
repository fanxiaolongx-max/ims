# IMS SIP 服务器 - 完整文档

## 📋 目录

1. [项目概述](#项目概述)
2. [快速开始](#快速开始)
3. [功能特性](#功能特性)
4. [日志系统](#日志系统)
5. [网络配置](#网络配置)
6. [RFC 3261 定时器](#rfc-3261-定时器)
7. [问题修复历史](#问题修复历史)
8. [测试建议](#测试建议)
9. [常见问题](#常见问题)
10. [RFC 3261 合规性](#rfc-3261-合规性)

---

## 项目概述

IMS SIP Server 是一个符合 RFC 3261 和 IMS 标准的 SIP 代理服务器，支持：

- ✅ SIP 基本方法：REGISTER, INVITE, ACK, BYE, CANCEL, OPTIONS, MESSAGE
- ✅ 扩展方法：PRACK, UPDATE, REFER, NOTIFY, SUBSCRIBE
- ✅ Record-Route 和 Route 处理
- ✅ NAT 穿越支持
- ✅ 异步 I/O 架构
- ✅ 完整的日志系统
- ✅ RFC 3261 定时器机制
- ✅ 内存自动清理

---

## 快速开始

### 安装依赖

```bash
# Python 3.7+
pip install -r requirements.txt
```

### 启动服务器

```bash
python run.py
```

### 配置服务器

编辑 `run.py` 中的配置：

```python
# 服务器配置
SERVER_IP = "127.0.0.1"  # 本机测试
SERVER_PORT = 5060

# 网络模式
FORCE_LOCAL_ADDR = True  # 本机测试模式
LOCAL_NETWORKS = ["127.0.0.1", "localhost"]

# 日志级别
log = init_logging(level="INFO", log_file="ims-sip-server.log")
```

---

## 功能特性

### 1. SIP 方法支持

| 方法 | 支持状态 | 说明 |
|------|---------|------|
| **REGISTER** | ✅ | 用户注册和注销 |
| **INVITE** | ✅ | 呼叫建立 |
| **ACK** | ✅ | 2xx 和非 2xx ACK（RFC 3261 合规） |
| **BYE** | ✅ | 呼叫终止 |
| **CANCEL** | ✅ | 呼叫取消 |
| **MESSAGE** | ✅ | 即时消息 |
| **OPTIONS** | ✅ | 能力查询 |
| **PRACK** | ✅ | 临时响应确认 |
| **UPDATE** | ✅ | 会话更新 |
| **REFER** | ✅ | 呼叫转移 |
| **NOTIFY** | ✅ | 事件通知 |
| **SUBSCRIBE** | ✅ | 事件订阅 |

### 2. 核心功能

#### 请求路由
- ✅ 初始请求：查找注册地址，改写 R-URI
- ✅ In-dialog 请求：使用 Route 头路由
- ✅ 环路检测：防止请求循环
- ✅ Max-Forwards 递减

#### 响应路由
- ✅ Via 头解析（支持 received 和 rport）
- ✅ NAT 地址修正
- ✅ Contact 头修正
- ✅ 错误响应过滤（482, 483, 502, 503, 504）

#### 对话管理
- ✅ DIALOGS 追踪：记录主叫和被叫地址
- ✅ PENDING_REQUESTS：记录请求发送者地址
- ✅ INVITE_BRANCHES：支持 CANCEL 的 Via branch 复用

#### Record-Route 处理
- ✅ 初始 INVITE 添加 Record-Route
- ✅ 2xx ACK 使用 Route 头
- ✅ 非 2xx ACK 保持原始 R-URI（RFC 3261 要求）

---

## 日志系统

### 日志级别

```python
log.debug("详细调试信息")
log.info("一般信息")
log.warning("警告信息")
log.error("错误信息")
log.critical("严重错误")
```

### SIP 专用日志方法

#### 接收消息 (RX)
```python
log.rx(("192.168.1.100", 5060), "INVITE sip:1002@example.com SIP/2.0")
# 输出: [RX] 192.168.1.100:5060 -> INVITE sip:1002@example.com SIP/2.0
```

#### 发送消息 (TX)
```python
log.tx(("192.168.1.100", 5060), "SIP/2.0 200 OK", extra="bindings=2")
# 输出: [TX] 192.168.1.100:5060 <- SIP/2.0 200 OK (bindings=2)
```

#### 转发消息 (FWD)
```python
log.fwd("INVITE", ("192.168.1.200", 5060), "R-URI=sip:1002@example.com")
# 输出: [FWD] INVITE -> 192.168.1.200:5060 R-URI=sip:1002@example.com
```

#### 丢弃消息 (DROP)
```python
log.drop("Loop detected: skipping self-forward")
# 输出: [DROP] Loop detected: skipping self-forward
```

### 日志文件

- **控制台输出**：彩色日志
- **文件输出**：`ims-sip-server.log`
- **建议**：生产环境使用 INFO 或 WARNING 级别

---

## 网络配置

### 模式 1：本机测试（默认）

```python
SERVER_IP = "127.0.0.1"
FORCE_LOCAL_ADDR = True
```

**适用场景**：
- 开发和测试环境
- 所有 UA 在同一台机器上

**行为**：
- 所有 Contact 地址转换为 `127.0.0.1`
- 简化本地调试

### 模式 2：局域网部署

```python
SERVER_IP = "192.168.1.100"  # 服务器实际 IP
FORCE_LOCAL_ADDR = False
LOCAL_NETWORKS = [
    "127.0.0.1",
    "localhost",
    "192.168.1.100",      # 服务器地址
    "192.168.1.0/24",     # 整个局域网段
]
```

**适用场景**：
- 生产环境
- 多个 UA 在不同机器上

**行为**：
- 保持 Contact 地址不变
- 使用真实的 IP 地址进行路由

### 模式 3：NAT 穿透

```python
SERVER_IP = "公网IP 或 NAT映射IP"
FORCE_LOCAL_ADDR = False
```

**注意**：NAT 环境可能需要 STUN/TURN/ICE 支持。

---

## RFC 3261 定时器

### 定时器概览

| 定时器 | 值 | 功能 |
|--------|-----|------|
| **Timer F** | 32s (64*T1) | 非 INVITE 事务超时 |
| **Timer H** | 32s (64*T1) | 等待 ACK 超时 |
| **DIALOG_TIMEOUT** | 3600s (1小时) | 对话超时清理 |
| **PENDING_CLEANUP** | 300s (5分钟) | 待处理请求清理 |
| **BRANCH_CLEANUP** | 60s (1分钟) | INVITE branch 检查间隔 |
| **REGISTRATION_CHECK** | 30s | 注册绑定检查间隔 |

### 自动清理功能

#### 1. 待处理请求清理（Timer F）
- **清理条件**：请求在 PENDING_REQUESTS 中超过 5 分钟
- **日志示例**：
  ```
  [TIMER-F] Cleaned up expired pending request: abc123... (age: 300.5s)
  ```

#### 2. 对话状态清理
- **清理条件**：对话在 DIALOGS 中超过 1 小时
- **日志示例**：
  ```
  [TIMER-DIALOG] Cleaned up stale dialog: xyz789... (age: 60.2min)
  ```

#### 3. INVITE Branch 清理（Timer H）
- **清理条件**：INVITE branch 存在超过 32 秒
- **日志示例**：
  ```
  [TIMER-H] Cleaned up INVITE branch: abc123... (branch: z9hG4bK-xxx, age: 32.5s)
  ```

#### 4. 注册绑定过期清理
- **清理条件**：Contact 绑定的 expires 时间已过
- **日志示例**：
  ```
  [TIMER-REG] Cleaned up 2 expired binding(s) for sip:1001@192.168.137.1
  ```

### 定时器配置

编辑 `sipcore/timers.py` 修改定时器参数：

```python
# RFC 3261 定时器常量
T1 = 0.5   # 500ms (RTT estimate)
T2 = 4.0   # 4s (max retransmit interval)
T4 = 5.0   # 5s (max message duration)

# 应用层定时器
DIALOG_TIMEOUT = 3600.0      # 1小时
PENDING_CLEANUP = 300.0      # 5分钟
BRANCH_CLEANUP = 60.0        # 1分钟
REGISTRATION_CHECK = 30.0    # 30秒
```

---

## 问题修复历史

### 1. UDP 网络错误修复

**问题**：`[WinError 1231] 不能访问网络位置`

**原因**：响应转发使用了不可达的外部 IP 地址。

**修复**：
- 新增 `PENDING_REQUESTS` 记录请求发送者地址
- 响应转发时优先使用记录的地址
- 添加 UDP 错误重试机制

### 2. 环路检测与 482 错误修复

**问题**：482 Loop Detected 响应不断转发。

**原因**：错误响应被重复转发，形成环路。

**修复**：
- 自动丢弃错误响应（482, 483, 502, 503, 504）
- ACK 请求 R-URI 修正（去除外部 IP 和 `;ob` 参数）

### 3. 响应路由修复

**问题**：100 Trying、180 Ringing 被错误地发回被叫。

**原因**：`PENDING_REQUESTS` 记录了转发目标地址（被叫），而不是请求发送者地址（主叫）。

**修复**：
```python
# 错误
PENDING_REQUESTS[call_id] = (host, port)  # 转发目标

# 正确
PENDING_REQUESTS[call_id] = addr  # 请求发送者
```

### 4. 486 循环重传修复

**问题**：486 Busy Here 响应不断重传，ACK 也重复转发。

**原因**：ACK 转发时添加了新的 Via branch，被叫无法匹配原始 INVITE 事务。

**修复**：
- ACK 使用无状态代理模式，不添加 Via 头
- 非 2xx ACK 的 R-URI 保持不变（RFC 3261 要求）

### 5. Record-Route 启用

**问题**：代理修改了 INVITE 的 R-URI，但没有添加 Record-Route。

**修复**：
- 启用 Record-Route（RFC 3261 强制要求）
- 2xx ACK 保留 Route 头，让正常路由逻辑处理

### 6. BYE 请求 481 错误修复

**问题**：BYE 请求收到 "481 Call/Transaction Does Not Exist"。

**原因**：
- 200 OK 发送后立即清理 DIALOGS
- ACK 到达时无法识别为 2xx ACK
- 2xx ACK 的 Route 头被错误删除

**修复**：
- 200 OK 后保留 DIALOGS，等待 ACK
- 移除删除 Route 头的代码
- 优化 ACK 类型判断逻辑

### 7. CANCEL 请求 481 错误修复

**问题**：CANCEL 请求收到 "481 Call/Transaction Does Not Exist"。

**原因**：
- CANCEL 的 R-URI 未修正
- CANCEL 的 Via branch 与 INVITE 不匹配

**修复**：
- 添加 CANCEL R-URI 修正逻辑
- 使用 `INVITE_BRANCHES` 复用 INVITE 的 Via branch

### 8. 200 OK (BYE) 循环修复

**问题**：200 OK (BYE) 被发回被叫，而不是 BYE 发起者。

**原因**：所有最终响应都强制路由到 `DIALOGS` 中的 caller_addr。

**修复**：
- 只对 INVITE 的最终响应使用 `DIALOGS` 路由
- 其他响应（如 BYE, CANCEL）使用 Via 头路由

### 9. MESSAGE 方法支持

**问题**：MESSAGE 请求未被转发，被环路检测拦截。

**原因**：MESSAGE 的 R-URI 指向服务器自己，没有像 INVITE 那样查找注册地址并改写 R-URI。

**修复**：
```python
# 修改前
if method == "INVITE" and _is_initial_request(msg):

# 修改后
if method in ("INVITE", "MESSAGE") and _is_initial_request(msg):
```

---

## 测试建议

### 推荐测试客户端

1. **Zoiper 5.x**（商业，免费版可用）
   - 下载：https://www.zoiper.com/
   - 优点：专业级，完全符合 RFC 3261

2. **Linphone**（开源，推荐）
   - 下载：https://www.linphone.org/
   - 优点：开源，RFC 3261 完全兼容

3. **MicroSIP**（轻量级）
   - 下载：https://www.microsip.org/
   - 优点：轻量级，开源

### 标准呼叫流程测试

#### 1. 成功呼叫
```
INVITE → 100 Trying → 180 Ringing → 200 OK → ACK → (通话) → BYE → 200 OK (BYE)
```

**测试步骤**：
1. 注册两个用户（1001, 1002）
2. 1001 呼叫 1002
3. 1002 接听
4. 通话中
5. 任意一方挂断

**预期结果**：
- ✅ INVITE 正确转发
- ✅ 临时响应发给主叫
- ✅ 200 OK 发给主叫
- ✅ ACK 到达被叫
- ✅ BYE 正确路由
- ✅ 200 OK (BYE) 发给 BYE 发起者

#### 2. 拒绝呼叫
```
INVITE → 100 Trying → 180 Ringing → 486 Busy Here → ACK
```

**测试步骤**：
1. 1001 呼叫 1002
2. 1002 拒绝

**预期结果**：
- ✅ 486 响应发给主叫
- ✅ ACK 到达被叫
- ✅ 486 不再重传

#### 3. 取消呼叫
```
INVITE → 100 Trying → 180 Ringing → CANCEL → 200 OK (CANCEL) → 487 Request Terminated → ACK
```

**测试步骤**：
1. 1001 呼叫 1002
2. 1002 振铃中
3. 1001 点击挂断

**预期结果**：
- ✅ CANCEL 正确转发
- ✅ 200 OK (CANCEL) 发给主叫
- ✅ 487 响应发给主叫
- ✅ ACK 到达被叫

#### 4. 即时消息
```
MESSAGE → 200 OK (MESSAGE)
```

**测试步骤**：
1. 1001 发送消息给 1002
2. 1002 收到消息

**预期结果**：
- ✅ MESSAGE 正确转发
- ✅ 200 OK 发给主叫
- ✅ 消息内容完整

### 网络环境测试

#### 本机测试
```bash
# 配置
SERVER_IP = "127.0.0.1"
FORCE_LOCAL_ADDR = True

# UA 配置
Domain: 127.0.0.1
Username: 1001
Password: 1234
```

#### 局域网测试
```bash
# 服务器配置
SERVER_IP = "192.168.137.1"
FORCE_LOCAL_ADDR = False
LOCAL_NETWORKS = ["192.168.137.0/24"]

# UA A (192.168.137.120)
Domain: 192.168.137.1
Username: 1001

# UA B (192.168.137.176)
Domain: 192.168.137.1
Username: 1002
```

---

## 常见问题

### Q1: 为什么 200 OK 后收不到 ACK？

**可能原因**：
1. UA 不支持 Record-Route
2. Contact 头地址不可达
3. UA 配置错误

**解决方案**：
1. 升级到支持 Record-Route 的 UA（如 Zoiper 5.x, Linphone）
2. 检查抓包，确认 200 OK 包含 Record-Route
3. 检查 ACK 是否发送到正确的地址

### Q2: 为什么 BYE 收到 481 错误？

**可能原因**：
1. 对话未正确建立（ACK 未到达）
2. 对话已超时清理
3. UA 发送了错误的 Call-ID

**解决方案**：
1. 确认 ACK 正确到达被叫
2. 检查日志中的 DIALOGS 状态
3. 验证 Call-ID 一致性

### Q3: 为什么 MESSAGE 不转发？

**原因**：服务器版本过旧，不支持 MESSAGE。

**解决方案**：更新到最新版本（已支持 MESSAGE）。

### Q4: 如何查看定时器运行状态？

```bash
# 实时查看定时器日志
tail -f ims-sip-server.log | grep TIMER

# 查看清理统计
grep "TIMER-CLEANUP" ims-sip-server.log
```

### Q5: 如何调整定时器参数？

编辑 `sipcore/timers.py`：

```python
# 缩短对话超时（从 1 小时改为 30 分钟）
DIALOG_TIMEOUT = 1800.0

# 加快注册检查（从 30 秒改为 15 秒）
REGISTRATION_CHECK = 15.0
```

### Q6: 内存持续增长怎么办？

**诊断**：
```bash
grep "TIMER-CLEANUP" ims-sip-server.log | tail -10
```

**可能原因**：
- 客户端发送请求后未处理响应
- 对话超时时间过长

**解决方案**：
1. 检查客户端行为
2. 降低 `PENDING_CLEANUP` 或 `DIALOG_TIMEOUT` 值
3. 启用 DEBUG 日志查看详细信息

---

## RFC 3261 合规性

### 已实现的 RFC 3261 要求

| 功能 | RFC 要求 | 实现状态 |
|------|---------|---------|
| **Record-Route** | 代理修改 R-URI 时必须添加 | ✅ |
| **2xx ACK Route** | 使用 Record-Route 构造 Route | ✅ |
| **非 2xx ACK** | R-URI 与 INVITE 相同 | ✅ |
| **Via 头处理** | 响应弹出顶层 Via | ✅ |
| **Max-Forwards** | 转发时递减 | ✅ |
| **Route 头处理** | 弹出指向自己的 Route | ✅ |
| **Contact 头** | 响应包含 Contact | ✅ |
| **无状态 ACK** | ACK 不添加 Via | ✅ |
| **Timer F** | 非 INVITE 事务超时 (32s) | ✅ |
| **Timer H** | 等待 ACK 超时 (32s) | ✅ |
| **环路检测** | 检测并阻止请求环路 | ✅ |
| **错误响应** | 482, 483 等错误响应处理 | ✅ |

### 信令流程合规性

#### INVITE 事务
```
主叫                服务器                被叫
  |                  |                    |
  |--- INVITE ------>|                    |
  |                  |--- INVITE -------->|
  |                  |    (+ Record-Route)|
  |                  |                    |
  |<-- 100 Trying ---|<-- 100 Trying -----|
  |<-- 180 Ringing --|<-- 180 Ringing ----|
  |<-- 200 OK -------|<-- 200 OK ---------|
  |    (+ Record-Route)                   |
  |                  |                    |
  |--- ACK --------->|                    |
  |    (+ Route)     |--- ACK ----------->|
  |                  |    (无 Via)        |
```

#### BYE 事务
```
主叫                服务器                被叫
  |                  |                    |
  |--- BYE --------->|                    |
  |    (+ Route)     |--- BYE ----------->|
  |                  |                    |
  |<-- 200 OK -------|<-- 200 OK ---------|
  |    (BYE)         |    (BYE)           |
```

#### CANCEL 事务
```
主叫                服务器                被叫
  |                  |                    |
  |--- INVITE ------>|--- INVITE -------->|
  |<-- 100 Trying ---|<-- 100 Trying -----|
  |                  |                    |
  |--- CANCEL ------>|--- CANCEL -------->|
  |    (same branch) |    (same branch)   |
  |                  |                    |
  |<-- 200 OK -------|<-- 200 OK ---------|
  |    (CANCEL)      |    (CANCEL)        |
  |                  |                    |
  |<-- 487 ----------|<-- 487 ------------|
  |    (INVITE)      |    (INVITE)        |
  |                  |                    |
  |--- ACK --------->|--- ACK ----------->|
  |    (non-2xx)     |    (preserved R-URI)|
```

---

## 相关文档

完整的修复历史和技术细节，请参考以下文档（已归档）：

- `LOGGING.md`: 日志系统详细说明
- `UDP_FIX.md`: UDP 网络错误修复
- `LOOP_FIX.md`: 环路检测修复
- `RFC3261_COMPLIANCE.md`: RFC 3261 合规性改进
- `NETWORK_MODE.md`: 网络模式配置
- `CONTACT_FIX.md`: Contact 头修正
- `RESPONSE_ROUTE_FIX.md`: 响应路由修复
- `ACK_ROUTING_ISSUE.md`: ACK 路由问题分析
- `ACK_RFC3261_FIX.md`: ACK RFC 3261 合规修复
- `ACK_ROUTE_FIX.md`: ACK Route 头修复
- `RECORD_ROUTE_DEBUG.md`: Record-Route 调试指南
- `FINAL_SUMMARY.md`: 修复完整总结
- `TIMERS.md`: 定时器详细说明
- `README_TIMERS.md`: 定时器快速开始
- `MESSAGE_SUPPORT.md`: MESSAGE 方法支持

---

## 总结

IMS SIP Server 是一个功能完整、符合 RFC 3261 标准的 SIP 代理服务器。主要特点：

✅ **完整的 SIP 支持**：REGISTER, INVITE, ACK, BYE, CANCEL, MESSAGE 等
✅ **RFC 3261 合规**：Record-Route, Route, Via, ACK 处理完全符合标准
✅ **NAT 穿越**：自动检测和修正 NAT 地址
✅ **内存管理**：RFC 3261 定时器自动清理过期状态
✅ **详细日志**：完整的 SIP 消息跟踪和调试信息
✅ **生产就绪**：异步 I/O, 错误处理, 优雅关闭

**适用场景**：
- 开发和测试环境
- 局域网 SIP 代理
- IMS P-CSCF 功能验证
- SIP 协议学习和研究

**不适用场景**：
- 大规模生产环境（建议使用 Kamailio, OpenSIPS 等成熟方案）
- 复杂的 NAT 环境（需要 STUN/TURN 支持）
- 高并发场景（当前为单线程异步架构）

---

**项目状态**：✅ 稳定可用
**RFC 3261 合规性**：✅ 完全合规
**最后更新**：2025-10-27


