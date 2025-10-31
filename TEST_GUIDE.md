# SIP 服务器自动化测试指南

## 概览

`test_sip_scenarios.py` 是一个自动化测试脚本，用于测试 SIP 服务器的各种场景，无需手动使用 SIP 客户端。

## 快速开始

### 1. 确保服务器运行

```bash
# 启动 SIP 服务器
python run.py
```

### 2. 运行所有测试

```bash
# 运行所有 10 个测试场景
python test_sip_scenarios.py
```

### 3. 运行单个测试

```bash
# 运行场景 1（正常呼叫）
python test_sip_scenarios.py 1

# 运行场景 5（即时消息）
python test_sip_scenarios.py 5
```

## 测试场景列表

| 编号 | 场景名称 | 说明 | 测试内容 |
|------|----------|------|----------|
| 1 | 正常呼叫 | 1001 呼叫 1002，通话 3 秒后挂断 | INVITE → 200 OK → ACK → BYE |
| 2 | 被叫忙 | 1001 呼叫 1002，模拟忙线 | INVITE → 486 Busy |
| 3 | 振铃时取消 | 1001 呼叫 1002，振铃期间取消 | INVITE → CANCEL |
| 4 | 被叫未注册 | 1001 呼叫未注册的 1003 | INVITE → 480 Unavailable |
| 5 | 即时消息 | 1001 发送消息给 1002 | MESSAGE → 200 OK |
| 6 | 注册注销 | 测试注册和注销流程 | REGISTER (401) → REGISTER (200) → REGISTER (Expires=0) |
| 7 | 错误密码 | 使用错误密码注册 | REGISTER → 401 → REGISTER (failed) |
| 8 | 并发呼叫 | 测试多个并发呼叫 | 多个 INVITE 同时进行 |
| 9 | 长时间通话 | 通话持续 10 秒 | 测试长时间会话稳定性 |
| 10 | 重复注册 | 用户多次注册刷新 | 测试注册刷新机制 |

## 配置修改

如果您的服务器配置不同，请修改脚本中的配置：

```python
# 在 test_sip_scenarios.py 文件顶部修改

SERVER_IP = "192.168.8.126"  # 您的服务器 IP
SERVER_PORT = 5060           # 您的服务器端口
LOCAL_IP = "127.0.0.1"       # 测试客户端 IP

# 测试用户（需要在 data/users.json 中存在）
USERS = {
    "1001": {"password": "1234", "port": 5061},
    "1002": {"password": "1234", "port": 5062},
    "1003": {"password": "1234", "port": 5063},
}
```

## 输出示例

```
══════════════════════════════════════════════════════════════════
  场景: 正常呼叫 - 1001 呼叫 1002，通话 3 秒后主叫挂断
══════════════════════════════════════════════════════════════════

[1001] 注册中...
  ✓ 注册成功

[1002] 注册中...
  ✓ 注册成功

[1001] 呼叫 1002...
  → 100 Trying
  ✓ 200 OK 收到，对话已建立
  → ACK 已发送

  【通话中...】

[1001] 挂断呼叫...
  ✓ BYE 成功

[1001] 注销中...
  ✓ 注册成功

[2002] 注销中...
  ✓ 注册成功

  ✓ 场景 1 完成
```

## 检查测试结果

### 1. 查看 MML 界面

访问 http://localhost:8888，查看：
- 实时日志：查看 SIP 消息流
- 活跃呼叫：测试期间的呼叫状态
- CDR 记录：测试完成后查看话单

### 2. 查看 CDR 文件

```bash
# 查看今日 CDR
ls -la CDR/$(date +%Y-%m-%d)/

# 查看呼叫记录
cat CDR/$(date +%Y-%m-%d)/cdr_*.csv
```

### 3. 查看日志文件

```bash
# 查看实时日志
tail -f logs/$(date +%Y-%m-%d)/ims-sip-server.log
```

## 常见问题

### Q1: 测试失败 - Connection timeout

**原因**: 服务器未启动或 IP/端口配置错误

**解决**:
```bash
# 检查服务器是否运行
ps aux | grep run.py

# 检查端口是否监听
netstat -an | grep 5060

# 确认服务器 IP
ifconfig
```

### Q2: 注册失败 - 401 Unauthorized

**原因**: 用户不存在或密码错误

**解决**:
```bash
# 检查用户是否存在
cat data/users.json | grep 1001

# 通过 MML 添加用户
# 访问 http://localhost:8888
# 执行: ADD USER USERNAME=1001 PASSWORD=1001 STATUS=ACTIVE
```

### Q3: 呼叫失败 - 480 Temporarily Unavailable

**原因**: 被叫未注册

**解决**:
- 确保测试脚本先注册所有用户
- 检查 MML 界面中的注册用户列表

### Q4: 测试脚本卡住

**原因**: Socket 超时设置过长

**解决**:
- 修改脚本中的 `timeout` 参数
- 使用 Ctrl+C 中断脚本

## 扩展测试

### 添加新的测试场景

```python
def test_scenario_11_custom():
    """场景11: 自定义场景"""
    print_scenario("自定义场景 - 描述")
    
    client1 = SIPClient("1001", "1001", 5061)
    
    try:
        # 您的测试逻辑
        client1.register()
        # ...
        client1.unregister()
    finally:
        client1.close()
```

### 修改测试参数

```python
# 修改通话时长
time.sleep(10)  # 改为 10 秒

# 修改注册有效期
client.register(expires=1800)  # 30 分钟

# 自定义 SDP
custom_sdp = """
v=0
o=test 123 123 IN IP4 127.0.0.1
s=Custom SDP
c=IN IP4 127.0.0.1
t=0 0
m=audio 10000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""
call = client.invite("1002", sdp=custom_sdp)
```

## 性能测试

### 压力测试（并发注册）

```bash
# 创建 100 个并发注册
for i in {1..100}; do
    python test_sip_scenarios.py 6 &
done
wait
```

### 长时间稳定性测试

```bash
# 循环运行测试 100 次
for i in {1..100}; do
    echo "=== 第 $i 次测试 ==="
    python test_sip_scenarios.py 1
    sleep 5
done
```

## 调试技巧

### 1. 启用详细日志

修改脚本，打印原始 SIP 消息：

```python
def _send_and_receive(self, message: str, expect_response: bool = True):
    print(f"\n>>> 发送:\n{message}")  # 添加这行
    self.sock.sendto(message.encode('utf-8'), (SERVER_IP, SERVER_PORT))
    
    if expect_response:
        data, addr = self.sock.recvfrom(4096)
        print(f"\n<<< 接收:\n{data.decode('utf-8')}")  # 添加这行
        return self._parse_response(data)
```

### 2. 使用 Wireshark 抓包

```bash
# 抓取 SIP 流量
sudo tcpdump -i any -n port 5060 -w sip_test.pcap

# 使用 Wireshark 查看
wireshark sip_test.pcap
```

### 3. 检查服务器日志

```bash
# 实时查看日志
tail -f logs/$(date +%Y-%m-%d)/ims-sip-server.log | grep -E "ERROR|WARNING"
```

## 持续集成

### GitHub Actions 示例

```yaml
# .github/workflows/sip-test.yml
name: SIP Server Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start SIP Server
        run: python run.py &
        
      - name: Wait for server
        run: sleep 5
      
      - name: Run tests
        run: python test_sip_scenarios.py
```

## 贡献

欢迎添加新的测试场景！请确保：

1. 场景有清晰的描述
2. 包含适当的错误处理
3. 清理资源（注销、关闭 socket）
4. 添加到场景列表中

---

**最后更新**: 2025-10-30

