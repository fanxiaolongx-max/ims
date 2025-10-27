# IMS SIP 服务器 - 快速开始

## 🚀 一键启动

```bash
cd /Volumes/512G/06-工具开发/ims
python run.py
```

启动后会自动：
1. ✅ 启动 SIP 服务器（UDP 5060）
2. ✅ 启动 Web 配置面板（HTTP 8080）
3. ✅ 自动打开浏览器访问配置页面

## 📱 测试客户端配置

### Zoiper 配置示例

| 项目 | 配置值 |
|------|--------|
| **服务器地址** | 192.168.8.126 |
| **端口** | 5060 |
| **传输协议** | UDP |
| **用户账号** | 1001 / 1002 / 1003 |
| **密码** | 1234 |
| **域** | 192.168.8.126 |

## 🌐 Web 配置面板

**访问地址**: http://127.0.0.1:8080

**功能：**
- 📊 查看所有配置参数（中文解释）
- 📈 实时运行状态
- 👥 用户列表
- 🔧 网络配置
- 📝 日志配置

## 📂 重要文件

```
ims/
├── run.py                  # 主程序（SIP 服务器）
├── web_config.py           # Web 配置面板
├── cdr_viewer.py           # CDR 查看工具
├── ims-sip-server.log      # 服务器日志
├── CDR/                    # CDR 话单目录
│   └── 2025-10-27/
│       └── cdr_2025-10-27.csv
└── sipcore/                # 核心模块
    ├── cdr.py              # CDR 记录系统
    ├── transport_udp.py    # UDP 传输层
    ├── parser.py           # SIP 消息解析
    └── ...
```

## 🔍 查看 CDR 话单

```bash
# 查看最近的通话记录
python cdr_viewer.py

# 查看指定日期的记录
python cdr_viewer.py --date 2025-10-27

# 查看详细统计
python cdr_viewer.py --stats
```

## 📝 查看日志

```bash
# 实时查看日志
tail -f ims-sip-server.log

# 查看最近的日志
tail -50 ims-sip-server.log

# 搜索错误
grep ERROR ims-sip-server.log
```

## 🛑 停止服务器

在运行窗口按 `Ctrl+C`

## 📚 完整文档

- [Web 配置面板使用说明](WEB_CONFIG_README.md)
- [CDR 系统说明](CDR_README.md)
- [CDR 去重优化](CDR_DEDUPLICATION.md)
- [网络错误处理](NETWORK_ERROR_HANDLING.md)
- [注册记录优化](REGISTER_CDR_FIX.md)

## ⚙️ 常用配置修改

### 1. 修改服务器 IP

编辑 `run.py`:
```python
SERVER_IP = "192.168.8.126"  # 修改为你的 IP
```

### 2. 添加用户

编辑 `run.py`:
```python
USERS = {
    "1001": "1234",
    "1002": "1234", 
    "1003": "1234",
    "1004": "5678"  # 新增用户
}
```

### 3. 修改 Web 端口

编辑 `web_config.py`:
```python
WEB_PORT = 8080  # 修改为其他端口
```

## 🎯 快速测试

### 1. 注册测试
```
客户端 1001 → 服务器 (REGISTER)
服务器 → 客户端 1001 (200 OK)
```

### 2. 呼叫测试
```
1001 → 服务器 → 1002 (INVITE)
1002 → 服务器 → 1001 (200 OK)
1001 → 服务器 → 1002 (ACK)
通话中...
1001 → 服务器 → 1002 (BYE)
1002 → 服务器 → 1001 (200 OK)
```

### 3. 查看结果
- Web 界面：查看实时状态
- CDR 文件：查看通话记录
- 日志文件：查看详细过程

---

**祝使用愉快！** 🎉

