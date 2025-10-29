# MML 管理界面

本目录包含 IMS SIP Server 的 MML（Man-Machine Language）管理界面。

---

## 🎯 什么是 MML？

MML（Man-Machine Language）是电信设备常用的命令行管理方式，被广泛应用于华为、爱立信等运营商级设备。

**特点：**
- 命令结构化、标准化
- 功能分类清晰
- 支持批量操作
- 便于脚本化管理
- 适合运维人员

---

## 📁 文件说明

### mml_server.py

MML 服务器后端，提供：
- HTTP 服务器（页面和 API）
- WebSocket 服务器（实时日志推送）
- 命令解析引擎
- 命令执行器

**端口：**
- HTTP: 8888（Web 界面）
- WebSocket: 8889（实时日志）

### mml_interface.html

MML Web 管理界面，包含：
- **左侧**：命令树（功能分类）
- **中间上方**：命令输出/回显区域
- **中间下方**：命令输入框
- **右侧**：实时日志显示

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install websockets psutil
```

### 2. 启动服务器

```bash
python run.py
```

MML 界面会自动启动。

### 3. 访问界面

打开浏览器访问：
```
http://localhost:8888
```

---

## 📚 MML 命令格式

### 基本格式

```
VERB OBJECT [PARAM1=VALUE1] [PARAM2=VALUE2] ...
```

**示例：**
```
DSP SYSINFO                    # 显示系统信息
DSP REG ALL                    # 显示所有注册
SET LOG LEVEL=DEBUG            # 设置日志级别
DSP CDR DATE=TODAY TYPE=CALL   # 显示今日呼叫 CDR
```

---

## 🔧 支持的命令

### 命令动词（VERB）

| 动词 | 说明 | 示例 |
|-----|------|------|
| **DSP** | 显示/查询 | DSP REG ALL |
| **ADD** | 添加 | ADD USER URI=sip:1001@ims.com |
| **RMV** | 删除 | RMV REG URI=sip:1001@ims.com |
| **MOD** | 修改 | MOD USER URI=sip:1001@ims.com |
| **SET** | 设置 | SET LOG LEVEL=INFO |
| **CLR** | 清除 | CLR REG ALL |
| **RST** | 重置 | RST SERVICE |
| **EXP** | 导出 | EXP CDR DATE=TODAY |
| **SAVE** | 保存 | SAVE CFG |
| **HELP** | 帮助 | HELP ALL |

---

## 📋 命令分类

### 1️⃣ 系统管理

```bash
# 查询系统信息
DSP SYSINFO

# 查询系统配置
DSP SYSCFG

# 修改日志级别
SET LOGLEVEL LEVEL=DEBUG

# 查询服务状态
DSP SRVSTAT

# 重启服务
RST SERVICE CONFIRM=YES
```

### 2️⃣ 用户管理

```bash
# 查询所有用户
DSP USER ALL

# 查询指定用户
DSP USER URI=sip:1001@ims.com

# 添加用户
ADD USER URI=sip:1001@ims.com PWD=1234 NAME=用户1

# 删除用户
RMV USER URI=sip:1001@ims.com CONFIRM=YES

# 修改用户密码
MOD USER URI=sip:1001@ims.com PWD=newpass
```

### 3️⃣ 注册管理

```bash
# 查询注册列表
DSP REG ALL

# 查询指定注册
DSP REG URI=sip:1001@ims.com

# 查询注册统计
DSP REG STAT

# 强制注销
RMV REG URI=sip:1001@ims.com CONFIRM=YES

# 清除所有注册
CLR REG ALL CONFIRM=YES
```

### 4️⃣ 呼叫管理

```bash
# 查询活跃呼叫
DSP CALL ACTIVE

# 查询呼叫统计
DSP CALL STAT

# 查询指定呼叫
DSP CALL CALLID=abc123...

# 强制挂断
RMV CALL CALLID=abc123... CONFIRM=YES

# 清除所有呼叫
CLR CALL ALL CONFIRM=YES
```

### 5️⃣ CDR 管理

```bash
# 查询今日 CDR
DSP CDR DATE=TODAY TYPE=CALL

# 查询指定日期 CDR
DSP CDR DATE=2025-10-27 TYPE=CALL

# 查询 CDR 统计
DSP CDR STAT DATE=2025-10-27

# 导出 CDR
EXP CDR DATE=2025-10-27 TYPE=CALL FORMAT=CSV

# 清理旧 CDR
CLR CDR BEFORE=2025-09-01 CONFIRM=YES
```

### 6️⃣ 配置管理

```bash
# 查询所有配置
DSP CFG ALL

# 查询指定配置
DSP CFG KEY=LOG_LEVEL

# 修改配置
SET CFG KEY=LOG_LEVEL VALUE=INFO

# 重置配置
RST CFG KEY=LOG_LEVEL CONFIRM=YES

# 保存配置
SAVE CFG
```

### 7️⃣ 性能监控

```bash
# 查询性能指标
DSP PERF ALL

# 查询 CPU 使用
DSP PERF CPU

# 查询内存使用
DSP PERF MEM

# 查询网络流量
DSP PERF NET

# 查询消息统计
DSP PERF MSG
```

### 8️⃣ 日志管理

```bash
# 查询日志配置
DSP LOG CFG

# 修改日志级别
SET LOG LEVEL=DEBUG

# 查询最近日志
DSP LOG RECENT LINES=50

# 搜索日志
DSP LOG SEARCH KEYWORD=ERROR

# 清理日志
CLR LOG BEFORE=2025-09-01 CONFIRM=YES
```

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|-------|------|
| `Enter` | 执行命令 |
| `↑` | 上一条命令（历史） |
| `↓` | 下一条命令（历史） |
| `Tab` | 命令自动完成（计划中）|

---

## 🎨 界面布局

```
┌─────────────────────────────────────────────────────────────┐
│ 🖥️ IMS MML 管理终端                     ⚫ 服务运行中  时间 │
├──────────┬────────────────────────────────┬─────────────────┤
│          │                                │                 │
│ 📚 命令树 │    命令输出/回显区域            │  📋 实时日志     │
│          │                                │                 │
│  系统管理 │  =============================  │  2025-10-27    │
│  用户管理 │  系统信息                       │  12:00:01 [INFO]│
│  注册管理 │  =============================  │  服务启动...    │
│  呼叫管理 │  服务器: IMS SIP Server        │                 │
│  CDR管理  │  版本: 2.0.0                   │  12:00:02 [INFO]│
│  配置管理 │  ...                           │  注册检查...    │
│  性能监控 │                                │                 │
│  日志管理 │                                │  12:00:03 [DEBUG│
│  帮助信息 │                                │  SIP 消息...    │
│          │                                │                 │
├──────────┴────────────────────────────────┴─────────────────┤
│ MML> DSP SYSINFO                                   [执行]   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 API 接口

### 获取命令树

```http
GET /api/command_tree
```

**响应：**
```json
{
  "系统管理": {
    "icon": "⚙️",
    "commands": {
      "查询系统状态": "DSP SYSINFO",
      ...
    }
  },
  ...
}
```

### 执行命令

```http
POST /api/execute
Content-Type: application/json

{
  "command": "DSP SYSINFO"
}
```

**响应：**
```json
{
  "retcode": 0,
  "retmsg": "Success",
  "output": "系统信息...",
  "timestamp": "2025-10-27 12:00:00"
}
```

---

## 🔧 扩展开发

### 添加新命令

编辑 `mml_server.py` 中的 `MMLCommandTree` 和 `MMLCommandExecutor`：

```python
# 1. 添加命令定义
class MMLCommandTree:
    @staticmethod
    def get_command_tree():
        return {
            "新分类": {
                "icon": "🆕",
                "commands": {
                    "新命令": "NEW CMD PARAM={value}"
                }
            }
        }

# 2. 添加命令处理器
class MMLCommandExecutor:
    def _handle_new(self, parts):
        # 实现命令逻辑
        return self._success_response("执行成功")
```

---

## 📊 与传统 Web 界面对比

| 特性 | 传统 Web 界面 | MML 界面 |
|-----|-------------|---------|
| **易用性** | 图形化，易上手 | 命令行，专业 |
| **效率** | 点击操作 | 命令输入，批量操作 |
| **脚本化** | 不支持 | 天然支持 |
| **运维友好** | 一般 | 非常友好 |
| **学习成本** | 低 | 中等 |
| **运营商适配** | 差 | 完美 |

---

## 💡 使用技巧

### 1. 命令历史

使用 `↑` `↓` 键快速调出历史命令。

### 2. 左侧命令树

点击左侧命令树中的命令，会自动填充到输入框。

### 3. 实时日志

右侧实时日志默认自动滚动，可以点击"暂停"按钮停止滚动。

### 4. 搜索命令

使用左侧顶部的搜索框快速定位命令。

---

## 🐛 故障排查

### WebSocket 连接失败

**问题**：右侧日志显示 "WebSocket 连接错误"

**原因**：websockets 库未安装

**解决**：
```bash
pip install websockets
```

### 命令执行失败

**问题**：命令返回错误

**解决**：
1. 检查命令格式是否正确
2. 查看参数是否完整
3. 输入 `HELP CMD=XXX` 查看帮助

---

## 📚 相关文档

- [MML 命令参考](../docs/MML_COMMAND_REFERENCE.md)（计划中）
- [IMS 发展路线图](../docs/IMS_ROADMAP.md)

---

**最后更新**：2025-10-27  
**版本**：1.0
