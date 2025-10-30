# IMS SIP Server

基于 RFC 3261 标准实现的 SIP 代理服务器，提供用户注册、呼叫控制、CDR 话单和 Web 管理功能。

## 快速开始

### 环境要求
- Python 3.7+
- 可选：websockets、psutil（MML 管理界面）

### 安装和启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd ims

# 2. 安装依赖（可选，MML 管理界面需要）
pip install -r requirements.txt

# 3. 启动服务
python run.py
```

启动后服务监听：
- SIP: UDP 5060
- MML 管理界面: HTTP 8888

### 访问管理界面

浏览器打开 http://localhost:8888

## 核心功能

### SIP 协议支持

| 方法 | 功能 | 状态 |
|------|------|------|
| REGISTER | 用户注册/注销 | ✓ |
| INVITE | 呼叫建立 | ✓ |
| ACK | 呼叫确认 | ✓ |
| BYE | 呼叫释放 | ✓ |
| CANCEL | 呼叫取消 | ✓ |
| OPTIONS | 能力查询 | ✓ |
| MESSAGE | 即时消息 | ✓ |

### CDR 话单系统

- 自动记录所有呼叫、注册、消息
- 按日期分文件夹归档（`CDR/YYYY-MM-DD/`）
- CSV 格式，包含主被叫、时长、状态等字段
- 支持通过 MML 查询、导出、清理

### 用户管理

- 用户增删改查（MML 命令或 Web 界面）
- 用户状态管理（ACTIVE/INACTIVE/SUSPENDED）
- 服务类型分级（BASIC/PREMIUM/VIP/ENTERPRISE）
- 支持批量导入（JSON 格式）

### MML 管理界面

基于 WebSocket 的实时管理界面，支持：

**命令管理**
- 用户管理：DSP USER, ADD USER, MOD USER, RMV USER
- 注册管理：DSP REG, RMV REG, CLR REG
- 呼叫管理：DSP CALL, RMV CALL, CLR CALL
- CDR 管理：DSP CDR, EXP CDR, CLR CDR
- 配置管理：DSP CFG, SET CFG, EXP CFG
- 性能监控：DSP PERF (CPU/MEM/NET/MSG)
- 日志管理：DSP LOG, SET LOG

**实时监控**
- 活跃呼叫数、注册用户数
- 实时日志推送（WebSocket）
- 系统性能指标（CPU、内存、网络）
- 命令历史记录

## 配置说明

### 服务器配置

编辑 `run.py`：

```python
SERVER_IP = "192.168.8.126"  # 服务器 IP
SERVER_PORT = 5060           # SIP 端口
FORCE_LOCAL_ADDR = False     # NAT 模式
```

或通过 MML 命令动态查询/修改：

```
DSP CFG                    # 查询所有配置
SET CFG KEY=LOG.LEVEL VALUE=INFO  # 修改日志级别
EXP CFG                    # 导出配置
```

### SIP 客户端配置

以 Linphone/Zoiper 为例：

```
Domain: <SERVER_IP>
Port: 5060
Username: 1001
Password: 1001
Transport: UDP
```

默认用户（`data/users.json`）：
- 1001/1001
- 1002/1002
- 1003/1003

## 目录结构

```
ims/
├── run.py                  # 主程序入口
├── requirements.txt        # 依赖列表
├── README.md              # 本文档
│
├── sipcore/               # SIP 协议核心
│   ├── parser.py         # 消息解析
│   ├── transport_udp.py  # UDP 传输
│   ├── auth.py           # Digest 认证
│   ├── cdr.py            # CDR 记录
│   ├── user_manager.py   # 用户管理
│   ├── logger.py         # 日志系统
│   └── sdp_parser.py     # SDP 解析
│
├── web/                   # MML 管理界面
│   ├── mml_server.py     # MML 后端服务
│   └── mml_interface.html # Web 前端
│
├── config/                # 配置管理
│   ├── config_manager.py # 配置管理器
│   └── config.json       # 配置文件
│
├── data/                  # 数据文件
│   └── users.json        # 用户数据
│
├── CDR/                   # 话单数据（按日期）
│   └── YYYY-MM-DD/
│       └── cdr_YYYY-MM-DD.csv
│
└── logs/                  # 日志文件（按日期）
    └── YYYY-MM-DD/
        └── ims-sip-server.log
```

## 典型场景

### 呼叫流程

```
成功呼叫:
INVITE -> 100 Trying -> 180 Ringing -> 200 OK -> ACK -> [通话] -> BYE -> 200 OK

取消呼叫:
INVITE -> 100 Trying -> 180 Ringing -> CANCEL -> 200 OK -> 487 Request Terminated -> ACK

拒绝呼叫:
INVITE -> 100 Trying -> 486 Busy Here -> ACK
```

### CDR 查询

通过 MML 界面：

```
DSP CDR                           # 查询今天的 CDR
DSP CDR DATE=2025-10-30           # 查询指定日期
DSP CDR TYPE=CALL LIMIT=50        # 查询呼叫类型，限制 50 条
EXP CDR DATE=2025-10-30 TYPE=CALL # 导出到 CSV
```

### 用户管理

```
DSP USER                                  # 查询所有用户
DSP USER USERNAME=1001                    # 查询指定用户
ADD USER USERNAME=1004 PASSWORD=1004      # 添加用户
MOD USER USERNAME=1004 STATUS=INACTIVE    # 修改用户状态
RMV USER USERNAME=1004 CONFIRM=YES        # 删除用户
```

## 日志管理

### 日志级别

- DEBUG: 详细调试信息
- INFO: 一般信息（默认）
- WARNING: 警告信息
- ERROR: 错误信息

修改日志级别：

```
# 方法 1: MML 命令
SET CFG KEY=LOG.LEVEL VALUE=DEBUG

# 方法 2: 编辑 config.json
{
  "LOG_LEVEL": "DEBUG"
}
```

### 日志格式

```
2025-10-30 12:34:56.789 [INFO    ] [run.py:handle_register:285] [RX] 192.168.8.120:5060 -> REGISTER
```

包含：时间戳（毫秒）、日志级别、源文件:函数:行号、消息内容

### 日志查看

```bash
# 实时查看
tail -f logs/2025-10-30/ims-sip-server.log

# 查看错误
grep ERROR logs/2025-10-30/ims-sip-server.log

# MML 查询
DSP LOG RECENT LINES=100
```

## 性能特性

- 并发注册支持：1000+
- 呼叫建立延迟：<100ms (LAN)
- 内存占用：~50MB (空闲)
- 日志限制：1000 条/页面 (MML)
- CDR 自动归档：按日期分文件夹

## 安全说明

**当前实现**：
- 密码明文存储（data/users.json）⚠️
- 无 TLS 加密传输 ⚠️
- MML 界面无认证 ⚠️
- 无请求频率限制 ⚠️

**建议**：
- 仅用于内网测试环境
- 生产部署前需完善安全机制
- 使用防火墙限制访问
- 定期备份数据

## RFC 3261 合规性

- ✓ Record-Route 处理
- ✓ Via 头管理
- ✓ ACK 路由（2xx 和非 2xx）
- ✓ NAT 检测和修正
- ✓ Digest 认证
- ✓ 呼叫状态机
- ✓ re-INVITE 支持（媒体切换）

## 测试建议

**推荐客户端**：
- Linphone (https://www.linphone.org/)
- Zoiper (https://www.zoiper.com/)
- MicroSIP (https://www.microsip.org/)

**测试场景**：
- 单用户注册/注销
- 点对点呼叫
- 呼叫取消
- 呼叫拒绝
- 即时消息
- re-INVITE（媒体切换）
- NAT 穿越

## 常见问题

**Q: 如何修改服务器端口？**
```python
# 编辑 run.py
SERVER_PORT = 5061
```

**Q: CDR 文件在哪里？**
```
CDR/2025-10-30/cdr_2025-10-30.csv
```

**Q: 如何清理旧日志？**
```bash
rm -rf logs/2025-09-*
```
或通过 MML：
```
CLR CDR BEFORE=2025-09-30 CONFIRM=YES
```

**Q: 服务启动失败？**
检查端口占用：
```bash
lsof -i :5060
netstat -tulpn | grep 5060
```

## 开发路线图

**P0 - 阻塞性问题**（商用前必须）：
- [ ] 密码加密存储（bcrypt + HA1）
- [ ] MML 界面认证
- [ ] NAT 穿越增强（STUN/TURN）
- [ ] 基础监控（健康检查、Prometheus）
- [ ] 容器化部署（Docker）

**P1 - 高优先级**（商用建议）：
- [ ] SIP 事务层完善
- [ ] REFER/SUBSCRIBE/NOTIFY 支持
- [ ] 并发安全改进
- [ ] 数据库迁移（SQLite/PostgreSQL）
- [ ] 完善文档

**P2 - 中优先级**（增强竞争力）：
- [ ] TLS/SIPS 支持
- [ ] RTP 媒体转发
- [ ] 多进程架构
- [ ] 计费系统
- [ ] 多租户支持

详见：商用化分析报告（咨询开发团队）

## 许可证

MIT License

## 版本历史

- v0.3 (2025-10-30): 完善 MML 管理功能、性能监控、配置管理
- v0.2 (2025-10-29): CDR 增强、re-INVITE 支持、日志优化
- v0.1 (2025-10-27): 初始版本，基础 SIP 功能

## 联系方式

如有问题或建议，请通过以下方式联系：
- Issue Tracker
- Email
- Pull Request

---

**项目状态**: 开发测试中  
**RFC 3261 合规性**: 基础合规  
**更新时间**: 2025-10-30
