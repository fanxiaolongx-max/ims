# 配置编辑功能 - 快速开始

## 🚀 30秒快速体验

### 步骤 1: 启动服务器

```bash
cd /Volumes/512G/06-工具开发/ims
python run.py
```

### 步骤 2: 打开测试页面

在浏览器中打开：
```
file:///Volumes/512G/06-工具开发/ims/web_config_edit_demo.html
```

### 步骤 3: 修改配置

1. 找到想修改的配置项
2. 点击"✏️ 编辑"按钮
3. 修改值
4. 点击"💾 保存"
5. 看到成功提示"✅ ..."

**完成！配置已生效，无需重启服务器！**

## 📝 快速示例

### 添加新用户

```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "USERS", "value": {"1001": "1234", "1002": "1234", "1003": "1234", "1004": "5678"}}'
```

**结果：** 用户 1004 立即可以注册，无需重启！

### 切换日志级别

```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOG_LEVEL", "value": "INFO"}'
```

**结果：** 日志输出立即减少，性能提升！

### 修改网络模式

```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "FORCE_LOCAL_ADDR", "value": false}'
```

**结果：** 从测试模式切换到生产模式，立即生效！

## ✅ 支持动态修改的配置

- ✅ **USERS** - 用户账号
- ✅ **FORCE_LOCAL_ADDR** - 网络模式
- ✅ **LOCAL_NETWORKS** - 本地网络列表
- ✅ **LOG_LEVEL** - 日志级别
- ✅ **CDR_MERGE_MODE** - CDR 合并模式

## ❌ 需要重启的配置

- ❌ **SERVER_IP** - 服务器 IP（需重启）
- ❌ **SERVER_PORT** - 服务器端口（需重启）

## 📚 完整文档

详细文档请参考：[WEB_CONFIG_EDIT_GUIDE.md](WEB_CONFIG_EDIT_GUIDE.md)

## 🎯 核心优势

1. **零停机** - 修改配置不影响业务
2. **即时生效** - 无需重启服务器
3. **持久化** - 自动保存到 config.json
4. **安全可靠** - 内置验证和错误处理

---

**开始使用吧！** 🎉

