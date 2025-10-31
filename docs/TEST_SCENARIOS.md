# SIP 服务器测试场景清单

## 测试场景概览

| 场景 | 名称 | SIP 方法 | 状态码 | 难度 | 测试时长 |
|------|------|----------|--------|------|----------|
| 1 | 正常呼叫 | REGISTER, INVITE, ACK, BYE | 200, 401 | ⭐⭐⭐ | ~5秒 |
| 2 | 被叫忙 | REGISTER, INVITE | 486 | ⭐⭐ | ~3秒 |
| 3 | 振铃时取消 | REGISTER, INVITE, CANCEL | 200, 487 | ⭐⭐⭐ | ~3秒 |
| 4 | 被叫未注册 | REGISTER, INVITE | 480 | ⭐⭐ | ~3秒 |
| 5 | 即时消息 | REGISTER, MESSAGE | 200, 401 | ⭐⭐ | ~2秒 |
| 6 | 注册注销 | REGISTER | 200, 401 | ⭐ | ~2秒 |
| 7 | 错误密码 | REGISTER | 401 | ⭐ | ~2秒 |
| 8 | 并发呼叫 | REGISTER, INVITE | 200, 401 | ⭐⭐⭐⭐ | ~3秒 |
| 9 | 长时间通话 | REGISTER, INVITE, ACK, BYE | 200, 401 | ⭐⭐⭐ | ~12秒 |
| 10 | 重复注册 | REGISTER | 200, 401 | ⭐⭐ | ~3秒 |

## 详细场景说明

### 场景 1: 正常呼叫

**测试目标**: 验证完整的呼叫流程

**流程**:
```
1001 → REGISTER → 401 → REGISTER (auth) → 200 OK
1002 → REGISTER → 401 → REGISTER (auth) → 200 OK
1001 → INVITE (to 1002) → 100/180 → 200 OK → ACK
     【通话 3 秒】
1001 → BYE → 200 OK
1001 → REGISTER (Expires: 0) → 200 OK
1002 → REGISTER (Expires: 0) → 200 OK
```

**验证点**:
- ✓ Digest 认证正常
- ✓ INVITE 正确路由到被叫
- ✓ Dialog 正确建立
- ✓ BYE 正确清理会话
- ✓ CDR 记录呼叫完整信息

**预期结果**:
- MML 界面显示通话记录
- CDR 文件包含完整话单
- 日志显示完整 SIP 流程

---

### 场景 2: 被叫忙

**测试目标**: 验证 486 Busy Here 处理

**流程**:
```
1001 → REGISTER → 200 OK
1002 → REGISTER → 200 OK
1001 → INVITE (to 1002) → 486 Busy Here
```

**验证点**:
- ✓ 服务器正确转发 486 响应
- ✓ 主叫收到忙音提示
- ✓ CDR 记录失败原因

**注意**: 当前服务器是 Proxy 模式，不会主动生成 486，需要被叫客户端返回

---

### 场景 3: 振铃时取消

**测试目标**: 验证 CANCEL 处理

**流程**:
```
1001 → REGISTER → 200 OK
1002 → REGISTER → 200 OK
1001 → INVITE (to 1002) → 100 Trying / 180 Ringing
     【等待 1 秒】
1001 → CANCEL → 200 OK → 487 Request Terminated
```

**验证点**:
- ✓ CANCEL 正确匹配 INVITE
- ✓ 服务器转发 CANCEL 到被叫
- ✓ 返回 487 Request Terminated
- ✓ CDR 记录取消原因

---

### 场景 4: 被叫未注册

**测试目标**: 验证 480 Temporarily Unavailable

**流程**:
```
1001 → REGISTER → 200 OK
1001 → INVITE (to 1003, 未注册) → 480 Temporarily Unavailable
```

**验证点**:
- ✓ 服务器检测到被叫未注册
- ✓ 返回 480 错误
- ✓ CDR 记录失败原因

---

### 场景 5: 即时消息

**测试目标**: 验证 MESSAGE 方法

**流程**:
```
1001 → REGISTER → 200 OK
1002 → REGISTER → 200 OK
1001 → MESSAGE (to 1002, text: "Hello...") → 200 OK
```

**验证点**:
- ✓ MESSAGE 正确路由到被叫
- ✓ 消息内容正确传递
- ✓ CDR 记录消息内容

---

### 场景 6: 注册注销

**测试目标**: 验证基本注册流程

**流程**:
```
1001 → REGISTER → 401 Unauthorized
1001 → REGISTER (with auth) → 200 OK
1001 → REGISTER (Expires: 0) → 200 OK
```

**验证点**:
- ✓ Digest 认证流程正确
- ✓ 注册信息正确存储
- ✓ 注销正确清理绑定
- ✓ CDR 记录注册/注销事件

---

### 场景 7: 错误密码

**测试目标**: 验证认证失败处理

**流程**:
```
1001 → REGISTER → 401 Unauthorized
1001 → REGISTER (wrong password) → 401 Unauthorized (认证失败)
```

**验证点**:
- ✓ 服务器拒绝错误密码
- ✓ 返回 401 错误
- ✓ 不允许注册

---

### 场景 8: 并发呼叫

**测试目标**: 验证多个并发会话

**流程**:
```
1001, 1002, 1003 同时 → REGISTER → 200 OK
1001 → INVITE (to 1002) → 并发处理
```

**验证点**:
- ✓ 服务器支持多个并发注册
- ✓ 服务器支持多个并发呼叫
- ✓ Dialog 隔离正确

**注意**: 当前简化实现，完整版需要多线程客户端

---

### 场景 9: 长时间通话

**测试目标**: 验证长时间会话稳定性

**流程**:
```
1001 → INVITE (to 1002) → 200 OK → ACK
     【通话 10 秒】
1001 → BYE → 200 OK
```

**验证点**:
- ✓ 长时间会话不超时
- ✓ Dialog 状态保持正确
- ✓ CDR 记录准确的通话时长

---

### 场景 10: 重复注册

**测试目标**: 验证注册刷新机制

**流程**:
```
1001 → REGISTER (Expires: 3600) → 200 OK
     【等待 1 秒】
1001 → REGISTER (Expires: 3600) → 200 OK (刷新)
```

**验证点**:
- ✓ 服务器接受重复注册
- ✓ 注册时间正确更新
- ✓ 不创建重复绑定

---

## 测试覆盖率

### SIP 方法覆盖

| 方法 | 覆盖场景 | 状态 |
|------|----------|------|
| REGISTER | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | ✓ 完全覆盖 |
| INVITE | 1, 2, 3, 4, 8, 9 | ✓ 完全覆盖 |
| ACK | 1, 9 | ✓ 基本覆盖 |
| BYE | 1, 9 | ✓ 基本覆盖 |
| CANCEL | 3 | ✓ 基本覆盖 |
| MESSAGE | 5 | ✓ 基本覆盖 |
| OPTIONS | - | ✗ 未覆盖 |
| REFER | - | ✗ 未覆盖 |
| NOTIFY | - | ✗ 未覆盖 |
| SUBSCRIBE | - | ✗ 未覆盖 |

### SIP 状态码覆盖

| 状态码 | 说明 | 覆盖场景 |
|--------|------|----------|
| 100 | Trying | 1, 3, 9 |
| 180 | Ringing | 1, 3, 9 |
| 200 | OK | 所有场景 |
| 401 | Unauthorized | 所有场景 |
| 480 | Temporarily Unavailable | 4 |
| 486 | Busy Here | 2 |
| 487 | Request Terminated | 3 |

### 功能覆盖

- ✓ 基础认证 (Digest)
- ✓ 用户注册/注销
- ✓ 呼叫建立/释放
- ✓ 呼叫取消
- ✓ 即时消息
- ✓ Dialog 管理
- ✓ CDR 记录
- ✓ NAT 处理
- ✗ TLS 加密
- ✗ 呼叫转移 (REFER)
- ✗ 呼叫保持 (re-INVITE)
- ✗ 订阅/通知 (SUBSCRIBE/NOTIFY)

---

## 扩展测试建议

### 建议添加的场景

1. **场景 11: re-INVITE (媒体切换)**
   - 测试呼叫中修改媒体参数
   - 验证 SDP 协商

2. **场景 12: PRACK (可靠临时响应)**
   - 测试 100rel 扩展
   - 验证可靠的 180 Ringing

3. **场景 13: UPDATE (会话更新)**
   - 测试不建立 dialog 的更新
   - 验证 SDP offer/answer

4. **场景 14: 呼叫转移 (REFER)**
   - 测试呼叫转接
   - 验证 NOTIFY 进度通知

5. **场景 15: NAT 穿越**
   - 测试不同 NAT 场景
   - 验证地址修正

6. **场景 16: 异常网络**
   - 测试丢包、延迟
   - 验证重传机制

7. **场景 17: 并发压力**
   - 100+ 并发注册
   - 50+ 并发呼叫

8. **场景 18: 恶意请求**
   - 测试非法 SIP 消息
   - 验证安全防护

---

## 测试最佳实践

### 测试顺序建议

1. **基础功能** (场景 6, 5)
   - 先测试最简单的注册和消息
   - 验证基础通信正常

2. **呼叫流程** (场景 1, 4)
   - 测试正常呼叫
   - 测试错误处理

3. **异常场景** (场景 2, 3, 7)
   - 测试各种失败情况
   - 验证错误响应

4. **压力测试** (场景 8, 9, 10)
   - 测试并发和稳定性
   - 验证长时间运行

### 测试环境准备

1. **清理环境**
   ```bash
   # 清理旧的 CDR
   rm -rf CDR/*
   
   # 清理日志
   rm -rf logs/*
   
   # 重启服务器
   pkill -f run.py && python run.py &
   ```

2. **准备用户**
   ```bash
   # 通过 MML 添加测试用户
   curl -X POST http://localhost:8888/mml \
     -d "ADD USER USERNAME=1001 PASSWORD=1001 STATUS=ACTIVE"
   ```

3. **验证配置**
   ```bash
   # 检查服务器 IP
   grep SERVER_IP run.py
   
   # 检查测试脚本 IP
   grep SERVER_IP test_sip_scenarios.py
   ```

### 测试结果验证

1. **查看实时日志**
   ```bash
   tail -f logs/$(date +%Y-%m-%d)/ims-sip-server.log
   ```

2. **检查 CDR**
   ```bash
   cat CDR/$(date +%Y-%m-%d)/cdr_*.csv | column -t -s,
   ```

3. **查看 MML 界面**
   ```
   http://localhost:8888
   ```

4. **使用 Wireshark 分析**
   ```bash
   sudo tcpdump -i any -n port 5060 -w sip.pcap
   wireshark sip.pcap
   ```

---

**最后更新**: 2025-10-30

