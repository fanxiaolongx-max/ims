# IMS SIP Server - 文档索引

技术文档导航和快速链接。

## 快速导航

### 📚 用户文档

| 文档 | 说明 | 适合 |
|------|------|------|
| [MML 管理界面](MML_GUIDE.md) | MML 命令行管理工具使用指南 | 运维人员 |
| [CDR 话单系统](CDR_README.md) | CDR 生成、查询、导出 | 运维/计费 |
| [日志系统](LOGGING.md) | 日志级别、格式、查看方式 | 运维人员 |
| [工具使用](TOOLS.md) | CDR 查看器等实用工具 | 运维/开发 |

### ⚙️ 配置文档

| 文档 | 说明 | 适合 |
|------|------|------|
| [配置管理](CONFIGURATION.md) | 服务器配置、动态配置 | 管理员 |
| [快速开始](QUICK_START.md) | 5 分钟快速启动 | 新用户 |

### 🔧 开发文档

| 文档 | 说明 | 适合 |
|------|------|------|
| [SIP 核心](SIP_CORE_README.md) | SIP 协议实现详情 | 开发人员 |
| [开发指南](DEVELOPMENT.md) | 架构设计、代码规范 | 开发人员 |
| [功能总结](FEATURE_SUMMARY.md) | 已实现功能清单 | 开发/运维 |

### 📝 修复说明

| 文档 | 说明 |
|------|------|
| [CDR 去重机制](CDR_DEDUPLICATION.md) | CDR 防重复记录 |
| [CDR 修复记录](CDR_FIX_NOTES.md) | 480 响应重复修复 |
| [注册 CDR 修复](REGISTER_CDR_FIX.md) | 401 认证合并修复 |
| [网络错误处理](NETWORK_ERROR_HANDLING.md) | 网络异常优雅处理 |
| [日志级别修复](BUG_FIX_LOG_LEVEL.md) | LOG_LEVEL 动态修改 |

### 📖 其他文档

| 文档 | 说明 |
|------|------|
| [更新日志](CHANGELOG.md) | 版本历史和功能更新 |
| [路线图](IMS_ROADMAP.md) | 开发计划和优先级 |

## 常用链接

### 新手入门
1. [README.md](../README.md) - 项目概览
2. [QUICK_START.md](QUICK_START.md) - 快速开始
3. [MML_GUIDE.md](MML_GUIDE.md) - MML 界面使用

### 日常运维
1. [MML 命令参考](MML_GUIDE.md#命令参考)
2. [CDR 查询导出](CDR_README.md#查询和导出)
3. [日志查看](LOGGING.md#日志查看)
4. [性能监控](MML_GUIDE.md#性能监控)

### 故障排查
1. [常见问题](../README.md#常见问题)
2. [网络错误处理](NETWORK_ERROR_HANDLING.md)
3. [日志分析](LOGGING.md#日志分析)

### 开发相关
1. [SIP 核心实现](SIP_CORE_README.md)
2. [CDR 系统设计](CDR_README.md)
3. [功能清单](FEATURE_SUMMARY.md)

## 文档维护

### 文档结构
```
docs/
├── README.md                    # 本文件 - 文档导航
├── CHANGELOG.md                 # 更新日志
│
├── 用户文档/
│   ├── MML_GUIDE.md            # MML 管理界面
│   ├── CDR_README.md           # CDR 话单系统
│   ├── LOGGING.md              # 日志系统
│   └── TOOLS.md                # 工具使用
│
├── 配置文档/
│   ├── CONFIGURATION.md        # 配置管理
│   └── QUICK_START.md          # 快速开始
│
├── 开发文档/
│   ├── SIP_CORE_README.md      # SIP 核心
│   ├── DEVELOPMENT.md          # 开发指南
│   └── FEATURE_SUMMARY.md      # 功能总结
│
└── 修复记录/
    ├── CDR_DEDUPLICATION.md    # CDR 去重
    ├── CDR_FIX_NOTES.md        # CDR 修复
    ├── REGISTER_CDR_FIX.md     # 注册修复
    ├── NETWORK_ERROR_HANDLING.md # 网络错误
    └── BUG_FIX_LOG_LEVEL.md    # 日志级别
```

### 贡献指南
- 新增文档请更新本索引
- 文档使用 Markdown 格式
- 代码示例使用正确的语法高亮
- 保持简洁专业的风格

---

**最后更新**: 2025-10-30

