# 📚 IMS SIP Server 文档索引

本目录包含 IMS SIP Server 的所有技术文档。

---

## 📖 文档分类

### 🚀 快速入门

| 文档 | 说明 | 适用对象 |
|-----|------|----------|
| [QUICK_START.md](QUICK_START.md) | Web 配置界面快速入门 | 所有用户 |
| [CONFIG_EDIT_QUICKSTART.md](CONFIG_EDIT_QUICKSTART.md) | 配置编辑快速指南 | 运维人员 |

---

### 📘 功能文档

| 文档 | 说明 | 内容概览 |
|-----|------|----------|
| [SIP_CORE_README.md](SIP_CORE_README.md) | SIP 协议核心实现 | 架构、路由、对话管理、RFC 3261 合规性 |
| [CDR_README.md](CDR_README.md) | CDR 话单系统 | 话单格式、记录类型、合并机制、查看工具 |
| [WEB_CONFIG_README.md](WEB_CONFIG_README.md) | Web 配置界面 | 界面功能、API 接口、状态监控 |
| [WEB_CONFIG_EDIT_GUIDE.md](WEB_CONFIG_EDIT_GUIDE.md) | 配置编辑指南 | 动态配置、参数说明、修改方法 |

---

### 🔧 技术说明

| 文档 | 说明 | 关键信息 |
|-----|------|----------|
| [CDR_DEDUPLICATION.md](CDR_DEDUPLICATION.md) | CDR 去重机制 | 防止重传导致的重复记录 |
| [NETWORK_ERROR_HANDLING.md](NETWORK_ERROR_HANDLING.md) | 网络错误处理 | 优雅处理网络不可达等错误 |

---

### 🐛 修复说明

| 文档 | 说明 | 修复内容 |
|-----|------|----------|
| [CDR_FIX_NOTES.md](CDR_FIX_NOTES.md) | 480 重复记录修复 | 防止 4xx/5xx 响应重传导致重复 CDR |
| [REGISTER_CDR_FIX.md](REGISTER_CDR_FIX.md) | 注册 CDR 修复 | 401 非失败、注册记录合并 |
| [BUG_FIX_LOG_LEVEL.md](BUG_FIX_LOG_LEVEL.md) | LOG_LEVEL 动态修改修复 | 修复 SIPLogger.setLevel 错误 |

---

### 📊 功能总结

| 文档 | 说明 | 用途 |
|-----|------|------|
| [FEATURE_SUMMARY.md](FEATURE_SUMMARY.md) | 所有功能总览 | 快速了解系统所有功能 |

---

## 🗂️ 按主题查找

### SIP 协议相关
- [SIP_CORE_README.md](SIP_CORE_README.md) - SIP 核心实现
  - SIP 方法支持（INVITE, BYE, REGISTER, MESSAGE 等）
  - 路由机制（初始请求、in-dialog 请求、响应路由）
  - 对话管理（DIALOGS, PENDING_REQUESTS）
  - NAT 处理
  - RFC 3261 合规性

### CDR 话单相关
- [CDR_README.md](CDR_README.md) - CDR 系统文档
  - 话单格式和字段说明
  - 记录类型
  - 合并模式
  - 查看工具
- [CDR_DEDUPLICATION.md](CDR_DEDUPLICATION.md) - CDR 去重机制
- [CDR_FIX_NOTES.md](CDR_FIX_NOTES.md) - 480 重复记录修复
- [REGISTER_CDR_FIX.md](REGISTER_CDR_FIX.md) - 注册 CDR 修复

### Web 配置相关
- [WEB_CONFIG_README.md](WEB_CONFIG_README.md) - Web 配置界面完整文档
- [WEB_CONFIG_EDIT_GUIDE.md](WEB_CONFIG_EDIT_GUIDE.md) - 配置编辑指南
- [QUICK_START.md](QUICK_START.md) - 快速入门
- [CONFIG_EDIT_QUICKSTART.md](CONFIG_EDIT_QUICKSTART.md) - 配置编辑快速指南

### 错误处理相关
- [NETWORK_ERROR_HANDLING.md](NETWORK_ERROR_HANDLING.md) - 网络错误处理
- [BUG_FIX_LOG_LEVEL.md](BUG_FIX_LOG_LEVEL.md) - LOG_LEVEL 修复

---

## 🎯 推荐阅读路径

### 新手入门
1. 📄 [../README.md](../README.md) - 项目主文档
2. 📄 [QUICK_START.md](QUICK_START.md) - 快速入门
3. 📄 [WEB_CONFIG_README.md](WEB_CONFIG_README.md) - Web 界面使用

### 运维人员
1. 📄 [WEB_CONFIG_EDIT_GUIDE.md](WEB_CONFIG_EDIT_GUIDE.md) - 配置管理
2. 📄 [CDR_README.md](CDR_README.md) - 话单管理
3. 📄 [NETWORK_ERROR_HANDLING.md](NETWORK_ERROR_HANDLING.md) - 故障处理

### 开发人员
1. 📄 [SIP_CORE_README.md](SIP_CORE_README.md) - 核心架构
2. 📄 [CDR_DEDUPLICATION.md](CDR_DEDUPLICATION.md) - 去重机制
3. 📄 [FEATURE_SUMMARY.md](FEATURE_SUMMARY.md) - 功能总览
4. 📄 所有修复说明文档

---

## 📝 文档维护

### 更新历史

| 日期 | 文档 | 变更 |
|-----|------|------|
| 2025-10-27 | 所有文档 | 创建统一文档归档系统 |
| 2025-10-27 | CDR_README.md | 添加合并模式说明 |
| 2025-10-27 | WEB_CONFIG_EDIT_GUIDE.md | 添加动态配置说明 |
| 2025-10-27 | 多个修复文档 | 记录问题修复过程 |

### 文档规范

- **文件名**: 使用 `UPPER_CASE.md` 格式
- **标题**: 使用 emoji 提升可读性
- **结构**: 包含目录、示例、代码片段
- **语言**: 简体中文
- **格式**: Markdown

---

## 🔗 相关资源

### 外部文档
- [RFC 3261 - SIP](https://www.rfc-editor.org/rfc/rfc3261)
- [RFC 3263 - SIP Server Location](https://www.rfc-editor.org/rfc/rfc3263)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)

### 工具推荐
- **Wireshark**: SIP 消息抓包分析
- **SIPp**: SIP 压力测试
- **Zoiper**: SIP 客户端测试

---

## 💡 使用提示

### 搜索文档

**按功能搜索：**
```bash
# 搜索 CDR 相关
grep -r "CDR" docs/*.md

# 搜索网络错误
grep -r "网络错误" docs/*.md

# 搜索配置相关
grep -r "配置" docs/*.md
```

**按代码示例搜索：**
```bash
# 查找包含代码块的文档
grep -l '```python' docs/*.md

# 查找特定函数
grep -r "handle_register" docs/*.md
```

### 生成文档目录

```bash
# 生成所有文档的目录树
tree docs/

# 按大小排序
ls -lhS docs/

# 按修改时间排序
ls -lt docs/
```

---

## 📞 获取帮助

如有文档相关问题：
- 📝 检查 [../README.md](../README.md) 常见问题部分
- 📧 联系项目维护者
- 💬 提交文档改进建议

---

**文档版本**: 2.0  
**最后更新**: 2025-10-27  
**维护者**: IMS SIP Server Team

