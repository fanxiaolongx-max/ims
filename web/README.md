# Web 配置界面

本目录包含 Web 配置管理界面相关文件。

## 📁 文件说明

### web_config.py

Web 配置服务器主程序，基于 Python 标准库 `http.server` 实现。

**功能：**
- 实时监控服务器状态
- 查看在线用户和活跃呼叫
- 动态配置参数修改
- REST API 接口

**API 端点：**
- `GET /` - Web 管理界面
- `GET /api/status` - 服务器状态
- `GET /api/config` - 当前配置
- `GET /api/config/editable` - 可编辑配置列表
- `POST /api/config/update` - 更新配置

### web_config_edit_demo.html

Web 配置界面的示例 HTML 页面，用于测试和演示。

## 🚀 启动方式

Web 配置界面会随主程序自动启动：

```bash
python run.py
```

默认端口：**8888**

访问地址：http://localhost:8888

## ⚙️ 配置

在 `run.py` 中可以修改 Web 端口：

```python
WEB_PORT = 8888  # 修改为其他端口
```

## 📚 相关文档

- [Web 配置完整文档](../docs/WEB_CONFIG_README.md)
- [配置编辑指南](../docs/WEB_CONFIG_EDIT_GUIDE.md)
- [快速开始](../docs/QUICK_START.md)

---

**技术栈**：Python http.server + HTML5 + CSS3 + JavaScript

