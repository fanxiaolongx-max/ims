# 独立的 SIP 客户端程序

完全独立于服务器代码的 SIP 客户端，用于自动外呼系统。

## 特性

- ✅ **完全独立**：不依赖服务器代码，可以单独运行
- ✅ **纯 Python**：仅使用标准库，无需外部依赖
- ✅ **RFC 3261 标准**：符合 SIP 协议标准
- ✅ **功能完整**：支持注册、呼叫、RTP 媒体播放
- ✅ **易于使用**：交互式命令行界面

## 快速开始

### 1. 配置文件

编辑 `sip_client_config.json`：

```json
{
  "server_ip": "192.168.8.126",
  "server_port": 5060,
  "username": "0000",
  "password": "0000",
  "local_ip": "192.168.8.126",
  "local_port": 10000,
  "media_dir": "media",
  "media_file": "media/default.wav"
}
```

### 2. 运行程序

```bash
python3 sip_client_standalone.py
```

### 3. 使用菜单

程序启动后会自动注册，然后显示交互式菜单：

```
============================================================
自动外呼系统 - 命令菜单
============================================================
1. 发起单次外呼
2. 批量外呼
3. 查看统计
4. 退出
```

## 程序结构

```
sip_client_standalone.py
├── SIPClient          # SIP 客户端核心类
│   ├── register()    # 注册到服务器
│   ├── invite()      # 发起呼叫
│   ├── bye()         # 挂断呼叫
│   └── send_ack()    # 发送 ACK
│
├── RTPPlayer         # RTP 媒体播放器
│   └── play_wav_file()  # 播放 WAV 文件
│
└── AutoDialerClient  # 自动外呼客户端
    ├── register()    # 注册
    └── dial()        # 发起外呼
```

## 作为库使用

您也可以在其他程序中使用这个客户端：

```python
from sip_client_standalone import AutoDialerClient

# 创建客户端
client = AutoDialerClient("sip_client_config.json")

# 注册
if client.register():
    # 发起外呼
    client.dial("1001", media_file="media/welcome.wav", duration=10.0)
    
    # 关闭
    client.close()
```

## 功能说明

### 注册流程

1. 发送 REGISTER（无认证）
2. 接收 401 Unauthorized
3. 发送 REGISTER（带 Digest 认证）
4. 接收 200 OK（注册成功）

### 呼叫流程

1. 发送 INVITE（带 SDP Offer）
2. 接收 180 Ringing（可选）
3. 接收 200 OK（带 SDP Answer）
4. 发送 ACK
5. 开始 RTP 媒体流
6. 发送 BYE 挂断

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `server_ip` | SIP 服务器 IP | `192.168.8.126` |
| `server_port` | SIP 服务器端口 | `5060` |
| `username` | SIP 用户名 | `0000` |
| `password` | SIP 密码 | `0000` |
| `local_ip` | 本地 IP 地址 | 自动检测 |
| `local_port` | 本地端口 | `10000` |
| `media_dir` | 媒体文件目录 | `media` |
| `media_file` | 默认媒体文件 | `media/default.wav` |

## 故障排除

### 注册失败

1. 检查服务器是否运行
2. 检查用户名和密码是否正确
3. 检查网络连接
4. 检查防火墙设置

### 呼叫失败

1. 确保已成功注册
2. 检查被叫用户是否存在
3. 检查被叫用户是否在线
4. 查看日志输出

## 注意事项

1. **端口冲突**：确保 `local_port` 未被其他程序占用
2. **媒体文件**：RTP 播放器目前是简化实现，实际需要解析 WAV 并转换为 RTP 数据包
3. **并发限制**：目前单线程处理，如需高并发，可以创建多个客户端实例

## 后续改进

- [ ] 完整的 RTP 媒体处理（WAV 解析、RTP 打包）
- [ ] 支持并发呼叫
- [ ] 支持视频呼叫
- [ ] 支持更多音频编解码器
- [ ] Web 界面管理

## 许可证

与主项目相同。

