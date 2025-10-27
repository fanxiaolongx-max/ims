# Web 配置面板使用说明

## 🌐 功能介绍

Web 配置面板是一个美观的可视化界面，用于展示 IMS SIP 服务器的所有配置参数和运行状态。

### 特点

- ✅ **零依赖** - 仅使用 Python 标准库，无需安装 Flask
- ✅ **自动启动** - 服务器启动时自动打开浏览器
- ✅ **美观设计** - 现代化的渐变背景和卡片式布局
- ✅ **实时状态** - 显示当前注册用户数、活动对话数等
- ✅ **中文解释** - 所有配置参数都有详细的中文说明
- ✅ **响应式** - 自动适配手机、平板、电脑屏幕

## 🚀 使用方法

### 1. 启动服务器

```bash
cd /Volumes/512G/06-工具开发/ims
python run.py
```

启动后会自动：
1. 打开浏览器访问 Web 配置面板
2. 显示访问地址：`http://127.0.0.1:8080`

### 2. 访问配置面板

如果浏览器没有自动打开，手动访问：

```
http://127.0.0.1:8080
```

或：

```
http://localhost:8080
```

## 📊 面板内容

### 🌐 基础配置
- **服务器 IP 地址**: SIP 服务器监听的 IP 地址
- **服务器端口**: SIP 信令监听端口（标准 5060）
- **服务器 URI**: 用于 Record-Route 头的完整 SIP URI

### 📡 SIP 协议能力
- **支持的方法**: 显示所有支持的 SIP 方法（INVITE, REGISTER, BYE 等）

### 🔧 网络环境配置
- **本地网络地址**: 不需要地址转换的本地/局域网地址列表
- **强制本地地址模式**: 
  - ✓ 启用：单机测试模式
  - ✗ 禁用：真实网络模式

### 👥 用户认证
- **注册用户列表**: 显示所有可注册的用户账号和密码

### 📊 CDR (话单记录)
- **CDR 存储目录**: 话单文件存储位置
- **记录合并模式**: 自动合并重复记录

### 📝 日志配置
- **日志级别**: 当前日志详细程度（DEBUG/INFO/WARNING/ERROR）
- **日志文件**: 日志输出文件路径

### ⚙️ 高级配置
- **默认注册过期时间**: 客户端未指定时的默认注册有效期
- **SIP 定时器**: INVITE 超时、注册过期、CDR 清理等定时任务

### 📈 运行状态（实时）
- **当前注册用户**: 已注册用户数 / 总用户数
- **活动对话**: 当前正在进行的通话数量
- **待处理请求**: 等待响应的 SIP 请求数量

## 🎨 界面预览

### 配色方案
- **背景**: 紫色渐变（#667eea → #764ba2）
- **卡片**: 白色圆角卡片，带阴影
- **强调色**: 蓝紫色（#667eea）
- **状态徽章**: 
  - 成功/启用：绿色
  - 警告：黄色
  - 信息：蓝色

### 动画效果
- ✨ 卡片淡入动画
- ✨ 卡片悬停上浮效果
- ✨ 状态徽章脉冲动画
- ✨ 响应式布局自动调整

## 🔌 API 接口

Web 面板提供 RESTful API 接口：

### GET `/`
返回 HTML 配置面板页面

### GET `/api/config`
返回 JSON 格式的配置数据

**示例请求：**
```bash
curl http://127.0.0.1:8080/api/config
```

**示例响应：**
```json
{
    "SERVER_IP": "192.168.8.126",
    "SERVER_PORT": 5060,
    "SERVER_URI": "sip:192.168.8.126:5060;lr",
    "ALLOW": "INVITE, ACK, CANCEL, BYE, OPTIONS...",
    "LOCAL_NETWORKS": ["127.0.0.1", "localhost", ...],
    "FORCE_LOCAL_ADDR": false,
    "USERS": {
        "1001": "1234",
        "1002": "1234",
        "1003": "1234"
    },
    "status": {
        "registered_users": 2,
        "active_dialogs": 0,
        "pending_requests": 0
    }
}
```

## ⚙️ 配置

### 修改端口

如果端口 8080 被占用，可以修改 `web_config.py`:

```python
# Web 服务器配置
WEB_HOST = '127.0.0.1'
WEB_PORT = 8080  # 修改这里
```

### 禁用自动打开浏览器

如果不想自动打开浏览器，注释掉 `web_config.py` 中的：

```python
# browser_thread = threading.Thread(target=open_browser, daemon=True)
# browser_thread.start()
```

或者在 `run.py` 中禁用 Web 界面：

```python
async def main():
    # 禁用 Web 配置界面
    # try:
    #     from web_config import init_web_interface
    #     init_web_interface()
    # except Exception as e:
    #     log.warning(f"Web interface failed to start: {e}")
    
    # 创建 UDP 服务器
    # ...
```

## 🛠️ 技术实现

### 后端
- **语言**: Python 3.7+
- **Web 框架**: Python 内置 `http.server.HTTPServer`
- **并发**: `threading` 模块实现后台运行
- **数据格式**: JSON

### 前端
- **HTML5** + **CSS3** + **原生 JavaScript**
- **Fetch API** 异步加载配置数据
- **CSS Grid** 响应式布局
- **CSS 动画** 流畅的交互效果

### 架构
```
run.py (SIP Server)
    ↓
web_config.py (Web Server)
    ├─ HTTP Server (8080)
    ├─ ConfigHandler
    │   ├─ GET / → HTML Page
    │   └─ GET /api/config → JSON Data
    └─ Browser Auto-open
```

## 📱 移动端支持

Web 面板完全支持移动设备：

- ✅ **iPhone/iPad**: Safari、Chrome
- ✅ **Android**: Chrome、Firefox
- ✅ **响应式设计**: 自动适配屏幕大小

### 移动端访问

1. 确保手机和服务器在同一局域网
2. 修改 `web_config.py` 中的 `WEB_HOST`:
   ```python
   WEB_HOST = '0.0.0.0'  # 允许外部访问
   ```
3. 在手机浏览器访问：`http://服务器IP:8080`

## ❓ 常见问题

### Q1: 浏览器没有自动打开？
**A**: 手动访问 `http://127.0.0.1:8080`，或检查是否有防火墙阻止。

### Q2: 端口 8080 被占用？
**A**: 修改 `web_config.py` 中的 `WEB_PORT` 为其他端口（如 8081、8888）。

### Q3: 能否修改配置？
**A**: 当前版本仅支持查看，不支持修改。修改配置请编辑 `run.py` 文件。

### Q4: 数据不更新？
**A**: 刷新浏览器页面（F5），Web 面板会重新加载最新数据。

### Q5: 能否关闭 Web 面板？
**A**: Web 服务器以守护线程运行，关闭 SIP 服务器时会自动关闭。如果想禁用，请参考"禁用自动打开浏览器"章节。

## 🎯 未来规划

- [ ] 支持在线修改配置
- [ ] 实时日志查看
- [ ] WebSocket 实时状态更新
- [ ] CDR 数据可视化图表
- [ ] 用户管理界面
- [ ] 呼叫统计和分析
- [ ] 暗黑模式切换

## 📞 联系与支持

如有问题或建议，欢迎反馈！

---

**版本**: v1.0  
**最后更新**: 2025-10-27  
**兼容性**: Python 3.7+, 所有现代浏览器

