# Web 配置编辑功能使用指南

## 🎉 功能概述

IMS SIP 服务器现已支持**动态配置修改**功能，可以在不重启服务器的情况下修改配置参数！

### ✨ 核心特性

- ✅ **动态修改** - 无需重启服务器，修改立即生效
- ✅ **持久化存储** - 配置自动保存到 `config.json` 文件
- ✅ **安全验证** - 内置参数验证，防止错误配置
- ✅ **不影响业务** - 修改过程不影响正在进行的呼叫
- ✅ **友好界面** - 简洁美观的 Web 编辑界面

## 📋 可修改的配置项

### ✅ 支持动态修改（无需重启）

| 配置项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **USERS** | dict | 用户账号和密码 | `{"1001": "1234", "1002": "5678"}` |
| **FORCE_LOCAL_ADDR** | bool | 强制本地地址模式 | `true` / `false` |
| **LOCAL_NETWORKS** | list | 本地网络地址列表 | `["127.0.0.1", "192.168.8.0/16"]` |
| **LOG_LEVEL** | str | 日志级别 | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| **CDR_MERGE_MODE** | bool | CDR 记录合并模式 | `true` / `false` |

### ❌ 不支持动态修改（需要重启）

| 配置项 | 类型 | 说明 | 原因 |
|--------|------|------|------|
| **SERVER_IP** | str | 服务器 IP 地址 | UDP socket 已绑定 |
| **SERVER_PORT** | int | 服务器端口 | UDP socket 已绑定 |

## 🚀 使用方法

### 方法 1: Web 界面编辑（推荐）

1. **启动服务器**
   ```bash
   cd /Volumes/512G/06-工具开发/ims
   python run.py
   ```

2. **打开编辑测试页面**
   ```
   打开浏览器访问：file:///Volumes/512G/06-工具开发/ims/web_config_edit_demo.html
   ```

3. **编辑配置**
   - 点击配置项右侧的"✏️ 编辑"按钮
   - 修改值
   - 点击"💾 保存"
   - 查看成功提示

### 方法 2: API 直接调用

#### 获取当前配置

```bash
curl http://127.0.0.1:8080/api/config
```

#### 获取可编辑配置项

```bash
curl http://127.0.0.1:8080/api/config/editable
```

#### 修改配置

**修改布尔值：**
```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "FORCE_LOCAL_ADDR", "value": true}'
```

**修改字符串：**
```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOG_LEVEL", "value": "INFO"}'
```

**修改用户列表：**
```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "USERS", "value": {"1001": "1234", "1002": "5678", "1004": "9999"}}'
```

**修改网络列表：**
```bash
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOCAL_NETWORKS", "value": ["127.0.0.1", "192.168.8.0/16", "10.0.0.0/8"]}'
```

## 📝 使用示例

### 示例 1: 动态添加用户

**场景：** 需要为新用户 1004 创建账号

```bash
# 1. 查看当前用户
curl -s http://127.0.0.1:8080/api/config | python -c "import sys, json; print(json.load(sys.stdin)['USERS'])"

# 2. 添加新用户 1004
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "USERS", "value": {"1001": "1234", "1002": "1234", "1003": "1234", "1004": "5678"}}'

# 3. 验证修改
curl -s http://127.0.0.1:8080/api/config | python -c "import sys, json; print(json.load(sys.stdin)['USERS'])"

# 4. 新用户 1004 可以立即注册和呼叫，无需重启服务器！
```

### 示例 2: 切换网络模式

**场景：** 从测试模式切换到生产模式

```bash
# 1. 禁用强制本地地址模式
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "FORCE_LOCAL_ADDR", "value": false}'

# 2. 添加生产网络地址
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOCAL_NETWORKS", "value": ["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8"]}'

# 完成！配置立即生效，无需重启
```

### 示例 3: 调整日志级别

**场景：** 生产环境减少日志输出

```bash
# 从 DEBUG 切换到 INFO
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOG_LEVEL", "value": "INFO"}'

# 日志级别立即生效，新的日志消息将使用 INFO 级别
```

## 🔒 安全性

### 配置验证

所有配置修改都会经过严格验证：

1. **类型检查**
   ```python
   # USERS 必须是 dict 类型
   # FORCE_LOCAL_ADDR 必须是 bool 类型
   # LOCAL_NETWORKS 必须是 list 类型
   ```

2. **值域检查**
   ```python
   # LOG_LEVEL 只能是 DEBUG/INFO/WARNING/ERROR
   # SERVER_PORT 必须在 1024-65535 范围内
   ```

3. **只读保护**
   ```python
   # SERVER_IP 和 SERVER_PORT 不可通过 API 修改
   # 返回错误：配置项不可修改（需要重启服务器）
   ```

### 错误处理

配置修改失败时会返回详细的错误信息：

```json
{
    "success": false,
    "message": "配置项 LOG_LEVEL 的值无效",
    "key": "LOG_LEVEL",
    "value": "INVALID"
}
```

## 📂 配置文件

### config.json

所有动态配置都保存在 `config.json` 文件中：

```json
{
    "USERS": {
        "1001": "1234",
        "1002": "1234",
        "1003": "1234",
        "1004": "5678"
    },
    "FORCE_LOCAL_ADDR": false,
    "LOCAL_NETWORKS": [
        "127.0.0.1",
        "localhost",
        "192.168.8.0/16"
    ],
    "LOG_LEVEL": "INFO",
    "CDR_MERGE_MODE": true
}
```

**特点：**
- ✅ 自动保存 - 每次修改自动写入
- ✅ 自动加载 - 服务器启动时自动读取
- ✅ 版本控制 - 可纳入 Git 管理
- ✅ 备份恢复 - 可手动编辑和恢复

## 🎯 最佳实践

### 1. 修改前备份

```bash
# 备份当前配置
cp config.json config.json.backup.$(date +%Y%m%d)
```

### 2. 批量修改策略

对于多个配置项的修改，建议逐个修改并验证：

```bash
# ✅ 推荐：逐个修改
curl -X POST ... -d '{"key": "USERS", "value": {...}}'
# 验证成功后再修改下一个
curl -X POST ... -d '{"key": "LOCAL_NETWORKS", "value": [...]}'

# ❌ 不推荐：同时修改多个（出错难以定位）
```

### 3. 生产环境修改

生产环境修改配置时的建议流程：

1. **测试环境验证** - 先在测试环境测试修改
2. **小范围试点** - 在生产环境小范围试点
3. **监控观察** - 观察日志和 CDR，确认无异常
4. **全量应用** - 确认无问题后全量应用

### 4. 配置回滚

如果修改后出现问题，快速回滚：

```bash
# 方法 1: 恢复备份文件
cp config.json.backup.20251027 config.json

# 方法 2: 通过 API 回滚单个配置
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "USERS", "value": {"1001": "1234", "1002": "1234", "1003": "1234"}}'
```

## ❓ 常见问题

### Q1: 修改后是否需要重启服务器？

**A**: 不需要！所有可动态修改的配置都会立即生效。只有 `SERVER_IP` 和 `SERVER_PORT` 需要重启。

### Q2: 修改用户列表后，旧用户会被踢出吗？

**A**: 不会。已注册的用户会保持连接，只是新的认证会使用新的用户列表。

### Q3: 配置文件被误删除怎么办？

**A**: 服务器会继续使用内存中的配置运行。可以通过 API 重新设置配置，会自动创建新的 `config.json` 文件。

### Q4: 可以添加新的配置项吗？

**A**: 可以。在 `config_manager.py` 的 `DYNAMIC_CONFIG` 中添加新的配置项定义，并在 `apply_config_change()` 中实现应用逻辑。

### Q5: 多个管理员同时修改配置会冲突吗？

**A**: 使用了线程锁保护，不会出现数据竞争。但最后的修改会覆盖之前的修改。

## 🔧 故障排查

### 问题 1: API 返回 404

**可能原因：**
- Web 服务器未启动
- 端口 8080 被占用

**解决方法：**
```bash
# 检查服务器是否运行
ps aux | grep "python.*run.py"

# 检查端口是否监听
lsof -i :8080
```

### 问题 2: 配置修改失败

**可能原因：**
- 参数类型错误
- 参数值无效

**解决方法：**
```bash
# 查看详细错误信息
curl -X POST http://127.0.0.1:8080/api/config/update \
  -H "Content-Type: application/json" \
  -d '{"key": "LOG_LEVEL", "value": "INVALID"}' 2>&1 | jq .message
```

### 问题 3: 配置没有生效

**可能原因：**
- 配置保存成功但应用失败
- 缓存未刷新

**解决方法：**
```bash
# 检查 config.json 文件内容
cat config.json

# 检查运行时配置
curl -s http://127.0.0.1:8080/api/config | jq .USERS

# 查看服务器日志
tail -f ims-sip-server.log | grep CONFIG
```

## 📚 参考资料

- [config_manager.py](config_manager.py) - 配置管理模块源码
- [web_config.py](web_config.py) - Web 接口实现
- [web_config_edit_demo.html](web_config_edit_demo.html) - 编辑界面示例

---

**版本**: v2.5  
**最后更新**: 2025-10-27  
**状态**: ✅ 生产就绪

