# 媒体截断（Media Relay）可行性分析

SIP 服务器从 Proxy 模式升级到 B2BUA + Media Relay 的技术分析文档。

## 概览

### 当前架构 vs 目标架构

**当前架构：SIP Proxy（信令代理）**

```
┌─────────┐                    ┌─────────┐
│  UA-A   │ ←─── 信令 ────────→ │  UA-B   │
│ (主叫) │                     │ (被叫) │
└─────────┘                    └─────────┘
     ↑                              ↑
     │         SIP Proxy            │
     │       (仅转发信令)           │
     └──────────┬─────────┬─────────┘
                │ run.py  │
                │ (5060)  │
                └─────────┘

媒体流向：UA-A ←──── RTP ────→ UA-B (直连)
         (通过 SDP 中协商的地址)
```

**目标架构：B2BUA + Media Relay（信令+媒体代理）**

```
┌─────────┐                    ┌─────────┐
│  UA-A   │ ←─── 信令 ────────→ │  UA-B   │
│ (主叫) │                     │ (被叫) │
└─────────┘                    └─────────┘
     ↑                              ↑
     │ SDP: 192.168.1.100:20000     │ SDP: 192.168.1.100:20002
     │                              │
     │         B2BUA + Media Relay  │
     │         (信令+媒体转发)      │
     └──────────┬─────────┬─────────┘
                │         │
        ┌───────┴─────────┴───────┐
        │   SIP Core (5060)       │
        │   RTP Relay (20000+)    │
        │   - 接收 RTP from A     │
        │   - 转发 RTP to B       │
        │   - 接收 RTP from B     │
        │   - 转发 RTP to A       │
        └─────────────────────────┘

媒体流向：UA-A ←→ Server ←→ UA-B (经过服务器)
```

### 核心差异对比

| 维度 | Proxy 模式 | B2BUA + Media Relay |
|------|-----------|---------------------|
| 信令处理 | 转发（保持 Call-ID） | 终结（生成新 Call-ID） |
| Via 头 | 累加（代理链） | 终结（两个独立会话） |
| SDP 修改 | 不修改 | 必须修改（改为服务器地址） |
| 媒体路径 | UA ←→ UA (直连) | UA ←→ Server ←→ UA |
| RTP 处理 | 不处理 | 接收、转发、可能转码 |
| 性能要求 | 低（仅信令） | 高（实时媒体流） |
| 实现复杂度 | 低 | 高 |
| 应用场景 | 简单代理 | 运营商级、录音、转码 |

---

## 实施步骤

### 第一阶段：信令层 B2BUA 改造（中等难度）

**难度**: ⭐⭐⭐  
**工作量**: 3-5 天  
**风险**: 中（可能破坏现有信令逻辑）

#### 步骤 1.1: B2BUA 架构设计

**当前**: Proxy 模式（单一 Call-ID，转发模式）  
**目标**: B2BUA 模式（双 Call-ID，终结模式）

关键改动：
- 为每个呼叫创建两个独立的 SIP Dialog
  - Call-ID-A: UA-A ↔ Server
  - Call-ID-B: Server ↔ UA-B
- 在 DIALOGS 中建立 Call-ID-A ↔ Call-ID-B 的映射
- 修改 `_forward_request/_forward_response` 逻辑
  - 不再简单转发，而是终结请求
  - 生成新的请求发往另一端

示例：
```
原来：INVITE (Call-ID: abc@A) → 转发 → INVITE (Call-ID: abc@A)
改为：INVITE (Call-ID: abc@A) → 服务器收到
      服务器生成 → INVITE (Call-ID: xyz@Server) → 发往 B
```

#### 步骤 1.2: Via 头处理改造

**当前**: 累加 Via（proxy 行为）  
**目标**: 终结 Via（B2BUA 行为）

改动：
- 收到请求：移除所有旧 Via，添加自己的 Via
- 发送响应：只使用自己的 Via
- 不再依赖 Via 路由链

#### 步骤 1.3: Contact 头改写

**当前**: 透传 Contact  
**目标**: 改写 Contact 为服务器地址

改动：
- INVITE 请求：`Contact: <sip:user@SERVER_IP:5060>`
- 200 OK 响应：`Contact: <sip:user@SERVER_IP:5060>`
- 确保后续请求（BYE/re-INVITE）发往服务器

---

### 第二阶段：SDP 修改（中等难度）

**难度**: ⭐⭐⭐⭐  
**工作量**: 5-7 天  
**风险**: 中高（SDP 格式复杂，易出错）

#### 步骤 2.1: SDP 解析增强

**当前**: 已有 `sdp_parser.py`（提取 call_type/codec）  
**目标**: 完整解析和修改 SDP

需要解析的字段：
- `c=` 行（连接地址）
- `m=` 行（媒体描述、端口）
- `a=rtpmap`（编解码映射）
- `a=fmtp`（编解码参数）
- `a=sendrecv/recvonly/sendonly`（媒体方向）

#### 步骤 2.2: 动态端口分配

设计：为每个呼叫分配一对 RTP/RTCP 端口

实现：
- 端口池：20000-30000（偶数给 RTP，奇数给 RTCP）
- 端口分配器：
  - `get_port_pair(call_id, leg)` → `(rtp_port, rtcp_port)`
  - leg: 'caller' 或 'callee'
- 端口释放：呼叫结束时回收端口

示例：
```
呼叫 1:
  caller leg: RTP=20000, RTCP=20001
  callee leg: RTP=20002, RTCP=20003
呼叫 2:
  caller leg: RTP=20004, RTCP=20005
  callee leg: RTP=20006, RTCP=20007
```

#### 步骤 2.3: SDP 改写逻辑

当前 INVITE 流程：
```
UA-A → INVITE (SDP: A的IP:端口) → 服务器 → INVITE → UA-B
```

改为：
```
UA-A → INVITE (SDP: A的IP:端口) → 服务器
       ↓ 解析 SDP
       ↓ 分配端口 20000/20001
       ↓ 改写 SDP: c=IN IP4 SERVER_IP
       ↓           m=audio 20000 RTP/AVP 0 8
       ↓ 记录映射: Call-ID-B → (20000, A的IP:端口)
服务器 → INVITE (SDP: SERVER_IP:20000) → UA-B

UA-B → 200 OK (SDP: B的IP:端口) → 服务器
       ↓ 解析 SDP
       ↓ 分配端口 20002/20003
       ↓ 改写 SDP: c=IN IP4 SERVER_IP
       ↓           m=audio 20002 RTP/AVP 0 8
       ↓ 记录映射: Call-ID-A → (20002, B的IP:端口)
服务器 → 200 OK (SDP: SERVER_IP:20002) → UA-A
```

结果：
- UA-A 认为对端是 `SERVER_IP:20002`
- UA-B 认为对端是 `SERVER_IP:20000`
- 服务器知道：
  - 20000 收到的包来自 A，转发到 B的实际地址
  - 20002 收到的包来自 B，转发到 A的实际地址

---

### 第三阶段：RTP/RTCP 媒体转发（高难度）⚠️

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 10-15 天  
**风险**: 高（实时性能、并发、丢包处理）

#### 步骤 3.1: RTP 协议栈实现

RTP 包格式：
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|X|  CC   |M|     PT      |       sequence number         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           timestamp                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           synchronization source (SSRC) identifier            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          payload ...                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

需要实现：
- RTP 包解析（头部 + payload）
- RTP 包校验（版本、序列号、时间戳）
- RTP 包转发（可能需要修改 SSRC）
- RTCP 包处理（SR/RR 报告）

#### 步骤 3.2: 媒体转发引擎

伪代码：
```python
class RTPRelay:
    def __init__(self):
        self.sessions = {}  # call_id → RTPSession
        self.sockets = {}   # port → socket
    
    async def start_session(self, call_id, port_a, addr_a, port_b, addr_b):
        """为呼叫启动 RTP 转发"""
        # 创建 socket 监听 port_a 和 port_b
        sock_a = create_udp_socket(port_a)
        sock_b = create_udp_socket(port_b)
        
        # 记录映射关系
        self.sessions[call_id] = {
            'a_port': port_a,
            'a_addr': addr_a,  # UA-A 的实际地址
            'b_port': port_b,
            'b_addr': addr_b,  # UA-B 的实际地址
            'sock_a': sock_a,
            'sock_b': sock_b
        }
        
        # 启动转发任务
        asyncio.create_task(self._relay_loop(call_id, 'a'))
        asyncio.create_task(self._relay_loop(call_id, 'b'))
    
    async def _relay_loop(self, call_id, leg):
        """转发循环"""
        session = self.sessions[call_id]
        if leg == 'a':
            recv_sock = session['sock_a']
            send_addr = session['b_addr']
        else:
            recv_sock = session['sock_b']
            send_addr = session['a_addr']
        
        while True:
            # 接收 RTP 包
            data, addr = await recv_sock.recvfrom(2048)
            
            # 验证来源（防止 RTP 注入攻击）
            expected_addr = session[f'{leg}_addr']
            if addr[0] != expected_addr[0]:
                log.warning(f"RTP from unexpected source: {addr}")
                continue
            
            # 转发到对端
            recv_sock.sendto(data, send_addr)
            
            # 统计流量
            session['bytes_relayed'] += len(data)
```

#### 步骤 3.3: RTCP 处理

RTCP 功能：
- SR (Sender Report): 发送端统计
- RR (Receiver Report): 接收端统计
- BYE: 会话结束通知

处理策略：
- 方案 1: 直接转发（简单，但统计不准）
- 方案 2: 终结 + 生成新 RTCP（复杂，统计准确）✅ 推荐

#### 步骤 3.4: NAT 穿透处理

问题：UA 可能在 NAT 后面，SDP 中的地址是内网地址

解决：
- 记录首个 RTP 包的来源地址（对称 RTP）
- 使用学习到的地址进行转发
- 支持 STUN/TURN（可选）

---

### 第四阶段：性能优化（高难度）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 15-20 天  
**风险**: 极高（稳定性、性能瓶颈）

#### 步骤 4.1: 多线程/多进程架构

问题：Python GIL 限制单线程性能

**方案 1**: 多线程（适合 I/O 密集型）
- SIP 信令线程
- RTP 转发线程池（每个呼叫一个线程）
- 缺点：GIL 可能成为瓶颈

**方案 2**: 多进程（适合 CPU 密集型）
- Master 进程：SIP 信令
- Worker 进程：RTP 转发
- 进程间通信：共享内存/消息队列
- 缺点：复杂度高

**方案 3**: 混合语言（✅ 推荐）
- Python: SIP 信令（run.py）
- C/C++: RTP 转发（高性能模块）
- 通过 ctypes/cffi 调用

#### 步骤 4.2: 异步 I/O

当前：同步 UDP socket  
目标：asyncio + uvloop

改动：
- 将 run.py 改为 asyncio
- 使用 `asyncio.DatagramProtocol` 处理 UDP
- 使用 uvloop 提升性能（2-4x）

#### 步骤 4.3: 内存优化

- 对象池（减少 GC 压力）
- 零拷贝转发（sendto 直接转发，不解析 payload）
- 限制并发呼叫数（防止内存耗尽）

---

## 技术选型建议

### 方案 A：纯 Python 实现

**优点**:
- 开发效率高
- 易于调试
- 代码统一（都是 Python）

**缺点**:
- 性能受限（GIL、解释型）
- 并发能力弱（≤ 50 并发呼叫）
- CPU 占用高

**适用场景**:
- 原型验证
- 小规模测试（< 10 并发呼叫）
- 功能演示

**推荐库**:
- aiortc: WebRTC 实现（包含 RTP）
- asyncio: 异步 I/O
- uvloop: 高性能事件循环

---

### 方案 B：Python + C/C++ 混合 ✅

**架构**:
- Python 层（run.py）:
  - SIP 信令处理
  - CDR 记录
  - MML 管理
  - SDP 解析/修改
- C/C++ 层（RTP 模块）:
  - RTP/RTCP 转发
  - 端口管理
  - 高性能 I/O

**优点**:
- 性能高（C/C++ 处理媒体）
- 易于维护（信令仍用 Python）
- 并发能力强（≥ 500 并发呼叫）

**缺点**:
- 开发复杂度高
- 需要跨语言调用
- 调试困难

**实现方式**:
- ctypes/cffi: Python → C 函数调用
- Cython: Python 代码编译为 C
- pybind11: C++ 模块暴露给 Python

---

### 方案 C：集成现有 RTP Proxy ✅✅ 最推荐

**架构**:
- IMS SIP Server (run.py):
  - SIP 信令（B2BUA）
  - SDP 修改
  - 通过 Socket 控制 RTP Proxy
- RTPProxy/RTPEngine (独立进程):
  - RTP/RTCP 转发
  - 端口管理
  - 性能优化

**优点**:
- 无需实现 RTP 栈（使用成熟方案）
- 性能极高（C 实现）
- 功能完整（NAT、录音、转码）
- 可独立扩展

**缺点**:
- 需要部署额外进程
- 需要学习控制协议

**推荐方案**:

**1. RTPProxy**
- 协议：简单文本协议
- 性能：高
- 功能：基础转发
- 适用：中小规模

**2. RTPEngine** ✅ 推荐
- 协议：JSON over UDP/TCP
- 性能：极高（多线程）
- 功能：转发、录音、转码、SRTP
- 适用：生产环境

**集成示例**:
```python
import socket
import json

def rtpengine_offer(call_id, sdp_offer):
    """发送 INVITE SDP 到 RTPEngine"""
    cmd = {
        "command": "offer",
        "call-id": call_id,
        "sdp": sdp_offer,
        "from-tag": "caller-tag",
        "flags": ["trust-address"]
    }
    sock.sendto(json.dumps(cmd).encode(), ('127.0.0.1', 22222))
    response = sock.recv(4096)
    return json.loads(response)['sdp']

def rtpengine_answer(call_id, sdp_answer):
    """发送 200 OK SDP 到 RTPEngine"""
    cmd = {
        "command": "answer",
        "call-id": call_id,
        "sdp": sdp_answer,
        "from-tag": "caller-tag",
        "to-tag": "callee-tag"
    }
    sock.sendto(json.dumps(cmd).encode(), ('127.0.0.1', 22222))
    response = sock.recv(4096)
    return json.loads(response)['sdp']

def rtpengine_delete(call_id):
    """呼叫结束，释放资源"""
    cmd = {
        "command": "delete",
        "call-id": call_id,
        "from-tag": "caller-tag"
    }
    sock.sendto(json.dumps(cmd).encode(), ('127.0.0.1', 22222))
```

---

## 工作量和时间估算

### 方案 A：纯 Python 实现

| 阶段 | 工作量 |
|------|--------|
| 第一阶段 - B2BUA 信令 | 5-7 天 |
| 第二阶段 - SDP 修改 | 7-10 天 |
| 第三阶段 - RTP 转发 | 15-20 天 |
| 第四阶段 - 性能优化 | 10-15 天 |
| 第五阶段 - 高级功能 (可选) | 20-30 天 |
| **总计（基础版）** | **37-52 天 (约 2 个月)** |
| **总计（完整版）** | **57-82 天 (约 3-4 个月)** |

### 方案 B：Python + C/C++ 混合

| 阶段 | 工作量 |
|------|--------|
| 第一阶段 - B2BUA 信令 | 5-7 天 |
| 第二阶段 - SDP 修改 | 7-10 天 |
| 第三阶段 - C++ RTP 模块 | 20-30 天 |
| 第四阶段 - Python 集成 | 10-15 天 |
| 第五阶段 - 性能优化 | 10-15 天 |
| **总计** | **52-77 天 (约 2.5-3.5 个月)** |

### 方案 C：集成 RTPEngine ✅✅ 最快

| 阶段 | 工作量 |
|------|--------|
| 第一阶段 - B2BUA 信令 | 5-7 天 |
| 第二阶段 - SDP 修改 | 7-10 天 |
| 第三阶段 - RTPEngine 集成 | 5-7 天 |
| 第四阶段 - 测试调优 | 5-7 天 |
| **总计** | **22-31 天 (约 1 个月)** |

---

## 风险和挑战

### 技术风险

| 风险项 | 风险等级 |
|--------|----------|
| RTP 实时性能要求（延迟 < 100ms） | ⚠️ 高 |
| Python GIL 性能瓶颈 | ⚠️ 高 |
| SDP 格式复杂，易出错 | ⚠️ 中 |
| NAT 穿透问题 | ⚠️ 中 |
| B2BUA 信令改造 | ⚠️ 低 |

### 稳定性风险

| 风险项 | 风险等级 |
|--------|----------|
| 丢包处理 | ⚠️ 高 |
| 并发稳定性 | ⚠️ 高 |
| 内存泄漏 | ⚠️ 中 |
| 异常恢复 | ⚠️ 中 |

### 兼容性风险

| 风险项 | 风险等级 |
|--------|----------|
| 不同 UA 的 SDP 格式差异 | ⚠️ 中 |
| 编解码支持 | ⚠️ 中 |
| SIP 信令兼容性（已有基础） | ⚠️ 低 |

---

## 建议和结论

### 难度评估

- **B2BUA 信令改造**: ⭐⭐⭐ (可行)
- **SDP 修改**: ⭐⭐⭐⭐ (较难)
- **RTP 转发 (纯Python)**: ⭐⭐⭐⭐⭐ (非常难，不推荐)
- **RTP 转发 (集成)**: ⭐⭐⭐ (推荐)

### 推荐方案

#### 🥇 方案 C: 集成 RTPEngine（最佳平衡）
- 开发时间最短（1 个月）
- 性能最好（生产级）
- 功能最完整（录音、转码等）
- 维护成本低（成熟方案）

#### 🥈 方案 B: Python + C++ 混合
- 完全可控（自己实现）
- 性能可接受（中等规模）
- 开发周期长（3 个月）

#### 🥉 方案 A: 纯 Python
- 仅适合原型验证
- 不适合生产环境
- 性能限制大（< 10 并发）

### 实施建议

**1. 第一阶段：先实现 B2BUA 信令（不改 RTP）**
- 验证架构可行性
- 积累 B2BUA 经验
- 工作量：1-2 周

**2. 第二阶段：集成 RTPEngine**
- 快速实现媒体转发
- 专注于 SIP 层逻辑
- 工作量：2-3 周

**3. 第三阶段：功能完善**
- 录音、统计、监控
- 异常处理、容错
- 工作量：1-2 周

### 总结

**容易做吗？**
- ✅ 信令层 B2BUA: 中等难度，可以做
- ✅ RTP 转发（集成方案）: 中等难度，推荐
- ❌ RTP 转发（自己实现）: 高难度，不推荐

**推荐路径：**
1. B2BUA 信令改造（1-2 周）
2. 集成 RTPEngine（2-3 周）
3. 功能完善和测试（1-2 周）

**总计：4-7 周可完成基础版本**

---

**最后更新**: 2025-10-30

