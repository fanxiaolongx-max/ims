# 📂 文档结构说明

本文档说明 IMS SIP Server 项目的文档组织结构。

---

## 📁 目录结构

```
ims/
│
├── README.md                    # 📘 项目主文档（从这里开始）
├── CHANGELOG.md                 # 📝 更新日志
├── DOCS_STRUCTURE.md           # 📂 本文件（文档结构说明）
│
├── run.py                       # 🚀 服务器主程序
├── config_manager.py           # ⚙️ 配置管理器
├── web_config.py               # 🌐 Web 配置界面
├── cdr_viewer.py               # 📊 CDR 查看工具
├── config.json                 # 💾 配置文件
│
├── sipcore/                     # 📦 SIP 核心模块
│   ├── parser.py               # 📝 SIP 消息解析
│   ├── transport_udp.py        # 🔌 UDP 传输层
│   ├── logger.py               # 📋 日志系统
│   ├── cdr.py                  # 📊 CDR 系统
│   └── timers.py               # ⏱️ 定时器
│
├── CDR/                         # 📊 CDR 话单目录
│   ├── 2025-10-27/             # 按日期组织
│   │   └── cdr_2025-10-27.csv
│   └── ...
│
└── docs/                        # 📚 技术文档目录
    ├── INDEX.md                # 📇 文档索引（推荐从这里开始浏览文档）
    │
    ├── 🚀 快速指南
    ├── QUICK_START.md          # 快速开始
    └── CONFIG_EDIT_QUICKSTART.md # 配置编辑快速指南
    │
    ├── 📘 功能文档
    ├── SIP_CORE_README.md      # SIP 核心实现
    ├── CDR_README.md           # CDR 系统
    ├── WEB_CONFIG_README.md    # Web 配置界面
    └── WEB_CONFIG_EDIT_GUIDE.md # 配置编辑指南
    │
    ├── 🔧 技术说明
    ├── CDR_DEDUPLICATION.md    # CDR 去重机制
    └── NETWORK_ERROR_HANDLING.md # 网络错误处理
    │
    ├── 🐛 修复说明
    ├── CDR_FIX_NOTES.md        # 480 重复记录修复
    ├── REGISTER_CDR_FIX.md     # 注册 CDR 修复
    └── BUG_FIX_LOG_LEVEL.md    # LOG_LEVEL 修复
    │
    └── 📊 功能总结
        └── FEATURE_SUMMARY.md  # 所有功能总览
```

---

## 📖 文档阅读顺序

### 🎯 新手用户

1. **开始使用**
   ```
   📘 README.md
   └─> 🚀 docs/QUICK_START.md
       └─> 🌐 docs/WEB_CONFIG_README.md
   ```

2. **了解功能**
   ```
   📊 docs/FEATURE_SUMMARY.md
   └─> 📊 docs/CDR_README.md
   ```

### 🛠️ 运维人员

1. **配置管理**
   ```
   ⚙️ docs/CONFIG_EDIT_QUICKSTART.md
   └─> 📝 docs/WEB_CONFIG_EDIT_GUIDE.md
   ```

2. **话单管理**
   ```
   📊 docs/CDR_README.md
   └─> 🔧 docs/CDR_DEDUPLICATION.md
   ```

3. **故障处理**
   ```
   🛡️ docs/NETWORK_ERROR_HANDLING.md
   └─> 🐛 所有修复说明文档
   ```

### 👨‍💻 开发人员

1. **核心架构**
   ```
   📘 docs/SIP_CORE_README.md
   └─> 📦 sipcore/ 源代码
   ```

2. **功能实现**
   ```
   📊 docs/FEATURE_SUMMARY.md
   └─> 🔧 docs/CDR_DEDUPLICATION.md
       └─> 🛡️ docs/NETWORK_ERROR_HANDLING.md
   ```

3. **问题修复**
   ```
   📝 CHANGELOG.md
   └─> 🐛 docs/CDR_FIX_NOTES.md
       └─> 🐛 docs/REGISTER_CDR_FIX.md
           └─> 🐛 docs/BUG_FIX_LOG_LEVEL.md
   ```

---

## 🗂️ 文档分类

### 按类型分类

| 类型 | 文档数量 | 文档列表 |
|-----|----------|----------|
| **快速指南** | 2 | QUICK_START, CONFIG_EDIT_QUICKSTART |
| **功能文档** | 4 | SIP_CORE_README, CDR_README, WEB_CONFIG_README, WEB_CONFIG_EDIT_GUIDE |
| **技术说明** | 2 | CDR_DEDUPLICATION, NETWORK_ERROR_HANDLING |
| **修复说明** | 3 | CDR_FIX_NOTES, REGISTER_CDR_FIX, BUG_FIX_LOG_LEVEL |
| **功能总结** | 1 | FEATURE_SUMMARY |

### 按主题分类

| 主题 | 相关文档 |
|-----|----------|
| **SIP 协议** | SIP_CORE_README |
| **CDR 系统** | CDR_README, CDR_DEDUPLICATION, CDR_FIX_NOTES, REGISTER_CDR_FIX |
| **Web 配置** | WEB_CONFIG_README, WEB_CONFIG_EDIT_GUIDE, QUICK_START, CONFIG_EDIT_QUICKSTART |
| **错误处理** | NETWORK_ERROR_HANDLING, BUG_FIX_LOG_LEVEL |
| **总览** | README, FEATURE_SUMMARY, CHANGELOG |

---

## 🔍 快速查找

### 我想了解...

| 需求 | 推荐文档 |
|-----|----------|
| **如何启动服务器** | README.md → 快速开始 |
| **如何配置服务器** | docs/WEB_CONFIG_README.md |
| **如何查看 CDR** | docs/CDR_README.md |
| **如何修改日志级别** | docs/CONFIG_EDIT_QUICKSTART.md |
| **SIP 协议实现细节** | docs/SIP_CORE_README.md |
| **CDR 如何防止重复** | docs/CDR_DEDUPLICATION.md |
| **网络错误如何处理** | docs/NETWORK_ERROR_HANDLING.md |
| **有哪些功能** | docs/FEATURE_SUMMARY.md |
| **版本更新内容** | CHANGELOG.md |

### 我遇到了...

| 问题 | 推荐文档 |
|-----|----------|
| **CDR 重复记录** | docs/CDR_DEDUPLICATION.md |
| **480 响应太多** | docs/CDR_FIX_NOTES.md |
| **401 注册失败** | docs/REGISTER_CDR_FIX.md |
| **网络不可达错误** | docs/NETWORK_ERROR_HANDLING.md |
| **日志级别修改失败** | docs/BUG_FIX_LOG_LEVEL.md |
| **其他问题** | README.md → 常见问题 |

---

## 📝 文档命名规范

### 文件命名

- **主要文档**: `README.md`, `CHANGELOG.md`
- **功能文档**: `XXX_README.md` 或 `XXX_GUIDE.md`
- **快速指南**: `QUICK_START.md`, `XXX_QUICKSTART.md`
- **修复说明**: `XXX_FIX_NOTES.md`, `BUG_FIX_XXX.md`
- **技术说明**: `XXX_HANDLING.md`, `XXX_MECHANISM.md`
- **总结文档**: `XXX_SUMMARY.md`
- **索引文档**: `INDEX.md`

### 标题规范

```markdown
# 文档标题

简短介绍（1-2句话）

---

## 📋 目录
...

## 章节标题
...
```

### emoji 使用

- 📘 主要文档
- 📚 文档集合
- 🚀 快速开始/启动
- ⚙️ 配置/设置
- 📊 数据/统计/CDR
- 🌐 Web/网络
- 🔧 技术/工具
- 🐛 Bug/修复
- ✨ 新功能
- 🛡️ 安全/错误处理
- 📝 日志/记录
- 🎯 目标/重点

---

## 🔄 文档更新流程

### 新增功能时

1. 更新 `CHANGELOG.md` - 添加版本记录
2. 创建或更新功能文档 - 详细说明
3. 更新 `README.md` - 简要说明
4. 更新 `docs/INDEX.md` - 添加索引
5. 更新 `docs/FEATURE_SUMMARY.md` - 添加功能列表

### 修复问题时

1. 创建修复说明文档 - `docs/XXX_FIX_NOTES.md`
2. 更新 `CHANGELOG.md` - 记录修复
3. 更新相关功能文档 - 补充说明
4. 更新 `docs/INDEX.md` - 添加索引

### 文档整理时

1. 检查文档结构 - 确保分类清晰
2. 更新索引文件 - `docs/INDEX.md`
3. 更新本文件 - `DOCS_STRUCTURE.md`
4. 检查链接 - 确保无死链

---

## 📊 文档统计

### 总览

- **根目录文档**: 3 个（README, CHANGELOG, DOCS_STRUCTURE）
- **docs 目录文档**: 13 个
- **总文档数**: 16 个
- **总字数**: 约 50,000 字
- **代码示例**: 100+ 个

### 覆盖范围

- ✅ SIP 协议实现
- ✅ CDR 系统
- ✅ Web 配置界面
- ✅ 网络错误处理
- ✅ 配置管理
- ✅ 问题修复记录
- ✅ 快速入门指南
- ✅ 功能总结

---

## 💡 使用建议

### 第一次使用

```
1. 阅读 README.md（10分钟）
   ↓
2. 跟随 docs/QUICK_START.md 启动服务（5分钟）
   ↓
3. 访问 Web 界面 http://localhost:8888（2分钟）
   ↓
4. 测试基本功能（注册、呼叫）（15分钟）
   ↓
5. 查看 CDR 记录（5分钟）
```

### 深入学习

```
1. 阅读 docs/FEATURE_SUMMARY.md（了解全部功能）
   ↓
2. 阅读 docs/SIP_CORE_README.md（理解 SIP 实现）
   ↓
3. 阅读 docs/CDR_README.md（理解 CDR 系统）
   ↓
4. 阅读修复说明文档（理解问题解决思路）
   ↓
5. 查看源代码（深入实现细节）
```

### 故障排查

```
1. 检查 README.md → 常见问题
   ↓
2. 查看日志文件（ims-sip-server.log）
   ↓
3. 搜索相关文档（grep 或 Web 搜索）
   ↓
4. 查看修复说明（docs/*FIX*.md）
   ↓
5. 提交 Issue（如问题未解决）
```

---

## 🔗 快速链接

### 主要入口
- 📘 [项目主页](../README.md)
- 📇 [文档索引](docs/INDEX.md)
- 📝 [更新日志](CHANGELOG.md)

### 常用文档
- 🚀 [快速开始](docs/QUICK_START.md)
- 📊 [CDR 系统](docs/CDR_README.md)
- 🌐 [Web 配置](docs/WEB_CONFIG_README.md)
- 📘 [SIP 核心](docs/SIP_CORE_README.md)

### 工具
- 📊 CDR 查看工具：`python cdr_viewer.py`
- 🌐 Web 界面：http://localhost:8888
- 📝 日志文件：`ims-sip-server.log`

---

## 📞 获取帮助

- 📖 阅读文档：从 [README.md](../README.md) 开始
- 📇 查看索引：[docs/INDEX.md](docs/INDEX.md)
- 📝 查看更新：[CHANGELOG.md](CHANGELOG.md)
- 💬 提交问题：Issues
- 📧 联系维护者：通过项目主页

---

**文档维护**: IMS SIP Server Team  
**最后更新**: 2025-10-27  
**版本**: 2.0.0

