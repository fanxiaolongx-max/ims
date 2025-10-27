# 项目结构

IMS SIP Server 的完整项目结构说明。

---

## 📁 目录树

```
ims/
│
├── 📄 核心文件
│   ├── run.py                      # 🚀 主程序入口
│   ├── README.md                   # 📘 项目文档
│   ├── requirements.txt            # 📦 依赖列表
│   ├── CHANGELOG.md                # 📝 更新日志
│   ├── DOCS_STRUCTURE.md           # 📂 文档结构说明
│   └── PROJECT_STRUCTURE.md        # 📊 本文件
│
├── 📦 config/ - 配置管理
│   ├── config_manager.py           # 配置管理器
│   ├── config.json                 # 配置数据文件
│   ├── __init__.py                 # Python 包标识
│   └── README.md                   # 配置模块说明
│
├── 🌐 web/ - Web 配置界面
│   ├── web_config.py               # Web 服务器主程序
│   ├── web_config_edit_demo.html   # 配置界面示例页面
│   ├── __init__.py                 # Python 包标识
│   └── README.md                   # Web 模块说明
│
├── 🛠️ tools/ - 工具脚本
│   ├── cdr_viewer.py               # CDR 查看和分析工具
│   ├── test_cdr.py                 # CDR 基础功能测试
│   ├── test_cdr_merged.py          # CDR 合并功能测试
│   ├── __init__.py                 # Python 包标识
│   └── README.md                   # 工具模块说明
│
├── 📦 sipcore/ - SIP 协议核心
│   ├── parser.py                   # SIP 消息解析器
│   ├── message.py                  # SIP 消息模型
│   ├── transport_udp.py            # UDP 传输层
│   ├── logger.py                   # 日志系统
│   ├── cdr.py                      # CDR 话单系统
│   ├── auth.py                     # SIP 认证模块
│   ├── timers.py                   # RFC 3261 定时器
│   ├── utils.py                    # 工具函数
│   └── __init__.py                 # Python 包标识
│
├── 📚 docs/ - 技术文档
│   ├── INDEX.md                    # 文档索引（推荐入口）
│   ├── SIP_CORE_README.md          # SIP 核心实现详解
│   ├── CDR_README.md               # CDR 系统完整文档
│   ├── CDR_DEDUPLICATION.md        # CDR 去重机制说明
│   ├── CDR_FIX_NOTES.md            # CDR 修复说明
│   ├── REGISTER_CDR_FIX.md         # 注册 CDR 修复
│   ├── NETWORK_ERROR_HANDLING.md   # 网络错误处理
│   ├── WEB_CONFIG_README.md        # Web 配置界面文档
│   ├── WEB_CONFIG_EDIT_GUIDE.md    # 配置编辑指南
│   ├── QUICK_START.md              # 快速开始指南
│   ├── CONFIG_EDIT_QUICKSTART.md   # 配置编辑快速指南
│   ├── BUG_FIX_LOG_LEVEL.md        # LOG_LEVEL 修复说明
│   └── FEATURE_SUMMARY.md          # 功能总结
│
├── 📊 CDR/ - 话单数据存储
│   ├── 2025-10-27/                 # 按日期组织
│   │   └── cdr_2025-10-27.csv      # 当日 CDR 文件
│   ├── 2025-10-28/
│   └── ...                         # 更多日期
│
├── 📋 logs/ - 日志文件
│   ├── ims-sip-server.log          # 服务器运行日志
│   └── README.md                   # 日志说明
│
└── 📤 export/ - 导出数据
    ├── cdr_export_today_CALL.csv   # 今日呼叫记录导出
    ├── cdr_export_today_MESSAGE.csv # 今日短信记录导出
    └── README.md                   # 导出说明
```

---

## 📊 目录说明

### 根目录文件

| 文件 | 说明 | 备注 |
|-----|------|------|
| `run.py` | 主程序入口 | 启动 SIP 服务器 |
| `README.md` | 项目主文档 | 从这里开始了解项目 |
| `requirements.txt` | Python 依赖 | pip install -r requirements.txt |
| `CHANGELOG.md` | 版本更新日志 | 详细的版本历史 |
| `DOCS_STRUCTURE.md` | 文档结构说明 | 文档组织说明 |
| `PROJECT_STRUCTURE.md` | 项目结构说明 | 本文件 |

### config/ - 配置管理

**职责**：管理服务器配置参数

| 文件 | 说明 |
|-----|------|
| `config_manager.py` | 配置管理器，支持动态配置更新 |
| `config.json` | 配置数据持久化文件 |
| `README.md` | 配置模块使用说明 |

**主要功能**：
- 配置参数定义和验证
- 配置持久化（JSON 格式）
- 动态配置更新（部分参数热更新）
- 配置 API 接口

### web/ - Web 配置界面

**职责**：提供 Web 管理界面

| 文件 | 说明 |
|-----|------|
| `web_config.py` | Web 服务器（基于 http.server）|
| `web_config_edit_demo.html` | 配置界面示例 |
| `README.md` | Web 模块使用说明 |

**主要功能**：
- 实时监控服务器状态
- 查看在线用户和活跃呼叫
- 动态配置参数修改
- REST API 接口

**默认端口**：8888

### tools/ - 工具脚本

**职责**：提供各种实用工具

| 文件 | 说明 | 用途 |
|-----|------|------|
| `cdr_viewer.py` | CDR 查看工具 | 查看、分析、导出 CDR |
| `test_cdr.py` | CDR 测试 | 测试 CDR 基础功能 |
| `test_cdr_merged.py` | CDR 合并测试 | 测试 CDR 合并功能 |
| `README.md` | 工具说明 | 使用方法 |

**使用方式**：
```bash
python tools/cdr_viewer.py --recent 10
python tools/test_cdr.py
```

### sipcore/ - SIP 协议核心

**职责**：SIP 协议实现核心

| 文件 | 说明 |
|-----|------|
| `parser.py` | SIP 消息解析器 |
| `message.py` | SIP 消息模型 |
| `transport_udp.py` | UDP 传输层（asyncio）|
| `logger.py` | 日志系统 |
| `cdr.py` | CDR 话单系统 |
| `auth.py` | SIP 认证（Digest）|
| `timers.py` | RFC 3261 定时器 |
| `utils.py` | 工具函数 |

**功能模块**：
- SIP 消息解析和生成
- UDP 异步传输
- 用户注册管理
- 呼叫路由和对话管理
- CDR 记录生成
- 认证和授权
- 定时器和内存清理

### docs/ - 技术文档

**职责**：项目技术文档

共 **13 个文档**，分为：
- **功能文档**（4个）：核心功能详细说明
- **快速指南**（2个）：快速入门和使用
- **技术说明**（2个）：技术实现细节
- **修复说明**（3个）：问题修复记录
- **总结文档**（2个）：功能和文档总览

**推荐阅读顺序**：
1. `INDEX.md` - 文档索引
2. `QUICK_START.md` - 快速开始
3. `SIP_CORE_README.md` - 核心实现
4. `CDR_README.md` - CDR 系统

### CDR/ - 话单数据存储

**职责**：存储 CDR 话单数据

**组织方式**：按日期组织
```
CDR/
├── 2025-10-27/
│   └── cdr_2025-10-27.csv
├── 2025-10-28/
│   └── cdr_2025-10-28.csv
...
```

**文件格式**：CSV（逗号分隔）

**保留策略**：建议定期归档或删除旧数据

### logs/ - 日志文件

**职责**：存储服务器运行日志

| 文件 | 说明 |
|-----|------|
| `ims-sip-server.log` | 主日志文件 |
| `README.md` | 日志说明 |

**日志级别**：DEBUG, INFO, WARNING, ERROR, CRITICAL

**日志轮转**：建议配置 logrotate

### export/ - 导出数据

**职责**：存储导出的 CDR 数据

**导出方式**：
```bash
python tools/cdr_viewer.py --export-today CALL
python tools/cdr_viewer.py --export-today MESSAGE
```

**文件命名**：`cdr_export_<日期>_<类型>.csv`

---

## 🔄 导入关系

### 主程序 (run.py)

```python
# 核心模块
from sipcore.parser import parse_message
from sipcore.transport_udp import UDPServer
from sipcore.logger import init_logging
from sipcore.cdr import init_cdr

# 配置管理
from config.config_manager import init_config_manager

# Web 界面
from web.web_config import init_web_interface
```

### Web 模块 (web/web_config.py)

```python
# 配置管理
from config.config_manager import apply_config_change
from config.config_manager import get_editable_configs
```

### 依赖关系图

```
run.py
├── sipcore/*           (SIP 核心)
├── config.*            (配置管理)
└── web.*               (Web 界面)
    └── config.*        (配置管理)

tools/cdr_viewer.py
└── sipcore.cdr         (CDR 系统)
```

---

## 📝 文件统计

| 类型 | 数量 | 说明 |
|-----|-----|------|
| **Python 源文件** | 15+ | 核心代码 |
| **配置文件** | 2 | config.json, requirements.txt |
| **文档文件** | 20+ | Markdown 文档 |
| **HTML 文件** | 1 | Web 界面 |
| **数据文件** | 动态 | CDR, logs, export |

---

## 🎯 设计原则

1. **功能分类**：按功能模块分目录
2. **职责单一**：每个目录职责明确
3. **文档齐全**：每个目录都有 README
4. **包结构**：添加 `__init__.py` 支持 Python 包导入
5. **路径清晰**：目录名称直观易懂
6. **易于维护**：结构清晰，便于扩展

---

## 📚 相关文档

- [项目主文档](README.md)
- [文档结构说明](DOCS_STRUCTURE.md)
- [文档索引](docs/INDEX.md)
- [更新日志](CHANGELOG.md)

---

## 💡 使用建议

### 新项目成员

1. 阅读 `README.md` - 了解项目概况
2. 查看 `PROJECT_STRUCTURE.md` - 了解目录结构
3. 阅读 `docs/INDEX.md` - 浏览技术文档
4. 运行 `python run.py` - 启动服务器

### 开发人员

1. 熟悉 `sipcore/` - 核心代码
2. 了解 `config/` 和 `web/` - 配置和界面
3. 使用 `tools/` - 辅助工具
4. 参考 `docs/` - 技术文档

### 运维人员

1. 配置 `config/config.json` - 服务器配置
2. 监控 `logs/` - 运行日志
3. 分析 `CDR/` - 话单数据
4. 使用 `tools/cdr_viewer.py` - CDR 分析

---

**最后更新**：2025-10-27  
**版本**：2.0.0

