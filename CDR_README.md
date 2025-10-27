# CDR（呼叫详单）系统使用说明

## 📋 概述

CDR（Call Detail Record）系统自动记录 IMS SIP 服务器上的所有终端行为，包括：

- ✅ **注册/注销** (REGISTER/UNREGISTER)
- ✅ **呼叫** (INVITE/BYE/CANCEL)
- ✅ **短信/消息** (MESSAGE)
- ✅ **心跳/能力查询** (OPTIONS)
- ✅ **其他 SIP 事件**

## 🎯 核心特性

### 记录合并模式（默认启用）

**同一次呼叫只产生一条 CDR 记录**，包含完整的呼叫流程信息：

```
传统模式（3条记录）:
1. CALL_START  - INVITE 开始
2. CALL_ANSWER - 200 OK 应答
3. CALL_END    - BYE 结束

✨ 合并模式（1条记录）:
1. CALL (ENDED) - 包含 INVITE, ANSWER, BYE 的完整时间戳
   - invite_time: 19:07:32.123
   - answer_time: 19:07:35.456  
   - bye_time:    19:08:20.789
   - duration:    45.3 秒
   - call_state:  ENDED
```

**优势：**
- ✅ 一目了然：一次呼叫只有一条记录
- ✅ 完整流程：记录各个阶段的精确时间戳
- ✅ 易于分析：减少记录数量，查询更快
- ✅ 便于计费：直接获取通话时长和状态

## 📁 文件组织

CDR 文件按日期自动组织，便于管理和归档：

```
CDR/
├── 2025-10-27/
│   └── cdr_2025-10-27.csv
├── 2025-10-28/
│   └── cdr_2025-10-28.csv
└── 2025-10-29/
    └── cdr_2025-10-29.csv
```

## 📊 CDR 字段说明（合并模式）

每条 CDR 记录包含以下标准字段（参考 3GPP TS 32.250/32.260）：

### 基本信息

| 字段名 | 说明 | 示例 |
|--------|------|------|
| record_id | 记录唯一ID | 20251027190732000001 |
| record_type | 记录类型 | CALL, REGISTER, MESSAGE, OPTIONS |
| call_state | 呼叫/事件状态 | STARTED, ANSWERED, ENDED, FAILED, CANCELLED |
| date | 日期 | 2025-10-27 |
| start_time | 开始时间 | 19:07:32 |
| end_time | 结束时间 | 19:08:25 |
| call_id | SIP Call-ID | gSpjxrh03Sw0A7EiSg1xJA.. |

### 主被叫信息

| 字段名 | 说明 | 示例 |
|--------|------|------|
| caller_uri | 主叫 URI | sip:1001@192.168.8.126 |
| caller_number | 主叫号码 | 1001 |
| caller_ip | 主叫 IP | 192.168.8.129 |
| caller_port | 主叫端口 | 57446 |
| callee_uri | 被叫 URI | sip:1002@192.168.8.126 |
| callee_number | 被叫号码 | 1002 |
| callee_ip | 被叫 IP | 192.168.8.120 |
| callee_port | 被叫端口 | 41303 |

### 呼叫详情（仅呼叫类型）

| 字段名 | 说明 | 示例 |
|--------|------|------|
| duration | 通话时长（秒） | 125.45 |
| setup_time | 呼叫建立时间（毫秒） | 2350 |
| invite_time | INVITE 时间 | 19:07:32.123 |
| ringing_time | 振铃时间 | 19:07:33.456 |
| answer_time | 应答时间 | 19:07:35.789 |
| bye_time | 结束时间 | 19:08:20.123 |
| status_code | SIP 最终状态码 | 200, 486, etc. |
| status_text | 状态描述 | OK, Busy Here, etc. |
| termination_reason | 终止原因 | Normal, User Cancelled, etc. |

### 其他信息

| 字段名 | 说明 | 示例 |
|--------|------|------|
| user_agent | 用户代理 | Zoiper v2.10 |
| contact | Contact 地址 | sip:1001@192.168.8.129:57446 |
| expires | 过期时间（注册） | 3600 |
| message_body | 消息内容（短信） | Hello World |
| server_ip | 服务器 IP | 192.168.8.126 |
| server_port | 服务器端口 | 5060 |
| cseq | CSeq | 1 INVITE |

## 🔍 CDR 记录类型与状态（合并模式）

### 记录类型 (record_type)

| 类型 | 说明 | 可能的状态 (call_state) |
|------|------|-------------------------|
| CALL | 呼叫记录 | STARTED, ANSWERED, ENDED, FAILED, CANCELLED |
| REGISTER | 注册记录 | SUCCESS, FAILED, UNREGISTERED |
| MESSAGE | 短信/消息 | COMPLETED |
| OPTIONS | 心跳/能力查询 | COMPLETED |

### 呼叫状态说明 (call_state for CALL)

| 状态 | 说明 | 包含的时间戳 |
|------|------|-------------|
| STARTED | 呼叫已发起但未应答 | invite_time |
| ANSWERED | 呼叫已应答 | invite_time, answer_time |
| ENDED | 呼叫正常结束 | invite_time, answer_time, bye_time, duration |
| FAILED | 呼叫失败 | invite_time, status_code (4xx/5xx/6xx) |
| CANCELLED | 呼叫被取消 | invite_time, termination_reason |

### 完整呼叫流程示例

```
记录类型: CALL
呼叫状态: ENDED
Call-ID: abc123...
开始时间: 19:07:32
结束时间: 19:08:25
INVITE 时间: 19:07:32.123
ANSWER 时间: 19:07:35.456
BYE 时间: 19:08:25.789
通话时长: 50.3 秒
状态码: 200
终止原因: Normal
```

## 🛠️ 使用 CDR 查看工具

### 安装

无需额外安装，CDR 系统已集成到 IMS SIP 服务器中。

### 基本命令

#### 1. 查看统计信息

```bash
# 查看今天的统计
python3 cdr_viewer.py stats

# 查看指定日期的统计
python3 cdr_viewer.py stats --date 2025-10-27
```

**输出示例：**
```
========== CDR 统计报告 - 今天 ================
📁 文件: CDR/2025-10-27/cdr_2025-10-27.csv
📊 总记录数: 156

📈 记录类型分布:
------------------------------------------------------------
  CALL_ANSWER              |    12 ( 7.7%) ███
  CALL_END                 |    10 ( 6.4%) ███
  CALL_START               |    15 ( 9.6%) ████
  REGISTER_SUCCESS         |   110 (70.5%) ███████████████████████████████████
  OPTIONS                  |     9 ( 5.8%) ██

📝 注册统计:
------------------------------------------------------------
  成功注册: 110
  失败注册: 0
  注销: 2

📞 呼叫统计:
------------------------------------------------------------
  呼叫开始: 15
  呼叫应答: 12
  呼叫结束: 10
  接通率: 80.0%
  平均通话时长: 45.3 秒
  总通话时长: 453.0 秒 (7.6 分钟)
```

#### 2. 查看最近的记录

```bash
# 查看最近 20 条记录
python3 cdr_viewer.py recent

# 查看最近 50 条记录
python3 cdr_viewer.py recent --limit 50

# 只查看呼叫开始记录
python3 cdr_viewer.py recent --type CALL_START

# 只查看注册成功记录
python3 cdr_viewer.py recent --type REGISTER_SUCCESS
```

#### 3. 查看特定呼叫详情

```bash
# 通过 Call-ID 查看呼叫的完整流程
python3 cdr_viewer.py call gSpjxrh03Sw0A7EiSg1xJA..
```

**输出示例：**
```
========== 呼叫详情 - gSpjxrh03Sw0A7EiSg1xJA.. ==========

记录 1: CALL_START
------------------------------------------------------------
  时间: 2025-10-27 19:07:32
  主叫: sip:1001@192.168.8.126 (1001)
  主叫地址: 192.168.8.129:57446
  被叫: sip:1002@192.168.8.126 (1002)
  被叫地址: 192.168.8.120:41303
  User-Agent: Zoiper v2.10

记录 2: CALL_ANSWER
------------------------------------------------------------
  时间: 2025-10-27 19:07:35
  建立时间: 3200 毫秒
  状态码: 200 OK

记录 3: CALL_END
------------------------------------------------------------
  时间: 2025-10-27 19:08:25
  通话时长: 50.5 秒
  终止原因: Normal
```

#### 4. 导出 CDR 数据

```bash
# 导出所有记录
python3 cdr_viewer.py export

# 导出特定类型的记录
python3 cdr_viewer.py export --type REGISTER_SUCCESS

# 导出到指定文件
python3 cdr_viewer.py export --output my_cdr.csv

# 导出指定日期的记录
python3 cdr_viewer.py export --date 2025-10-27 --type CALL_START
```

## 📈 应用场景

### 1. 计费系统

根据 CDR 中的通话时长、呼叫次数等信息进行计费：

```python
from sipcore.cdr import get_cdr

# 获取某个用户的通话时长
def calculate_call_duration(user_number, date):
    cdr = get_cdr()
    stats = cdr.get_stats(date)
    # 根据 CDR 数据计算...
```

### 2. 对账处理

- 统计每日呼叫量
- 计算接通率
- 分析失败原因

### 3. 问题排查

通过 Call-ID 追踪完整的呼叫流程，快速定位问题：

```bash
# 1. 查看最近的失败呼叫
python3 cdr_viewer.py recent --type CALL_FAIL

# 2. 根据 Call-ID 查看详细信息
python3 cdr_viewer.py call <Call-ID>
```

### 4. 业务分析

- 用户活跃度分析
- 呼叫高峰时段统计
- 短信发送量统计

## 🔧 高级用法

### 自定义 CDR 记录

在 `run.py` 中添加自定义 CDR 记录：

```python
from sipcore.cdr import get_cdr

cdr = get_cdr()

# 记录自定义事件
cdr.write_record(
    record_type="CUSTOM_EVENT",
    caller_uri="sip:1001@example.com",
    extra_info="自定义信息"
)
```

### 直接读取 CSV 文件

CDR 文件是标准的 CSV 格式，可以用 Excel、Python pandas 等工具直接打开：

```python
import pandas as pd

# 读取 CDR 文件
df = pd.read_csv('CDR/2025-10-27/cdr_2025-10-27.csv')

# 分析数据
print(df.describe())
print(df.groupby('record_type').size())
```

### 导入到数据库

```python
import sqlite3
import csv

conn = sqlite3.connect('cdr.db')
cursor = conn.cursor()

# 创建表
cursor.execute('''CREATE TABLE IF NOT EXISTS cdr (
    record_id TEXT PRIMARY KEY,
    record_type TEXT,
    timestamp TEXT,
    caller_number TEXT,
    callee_number TEXT,
    duration REAL,
    ...
)''')

# 导入 CDR
with open('CDR/2025-10-27/cdr_2025-10-27.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute('INSERT INTO cdr VALUES (...)', ...)

conn.commit()
```

## 📌 注意事项

1. **存储空间**: CDR 文件会随时间增长，建议定期归档或清理旧数据
2. **隐私保护**: CDR 包含敏感信息，请妥善保管
3. **性能**: CDR 写入是异步的，不影响 SIP 服务器性能
4. **备份**: 建议定期备份 CDR 目录

## 🆘 常见问题

**Q: CDR 文件在哪里？**  
A: 在项目根目录的 `CDR/` 文件夹下，按日期组织。

**Q: 如何清理旧的 CDR 文件？**  
A: 直接删除对应日期的文件夹即可，或使用脚本批量清理：
```bash
# 删除 30 天前的 CDR
find CDR -type d -mtime +30 -exec rm -rf {} \;
```

**Q: CDR 影响服务器性能吗？**  
A: 不会。CDR 写入使用了线程锁和异步机制，对性能影响极小。

**Q: 可以自定义 CDR 字段吗？**  
A: 可以。在 `sipcore/cdr.py` 的 `FIELDS` 列表中添加字段即可。

## 📚 参考标准

- 3GPP TS 32.250: Charging management; Charging data description for the IMS
- 3GPP TS 32.260: IP Multimedia Subsystem (IMS) charging
- RFC 7866: Session Recording Protocol
- RFC 3261: SIP: Session Initiation Protocol

## 📝 版本历史

- **v2.0 (2025-10-27)**: 🎉 **记录合并模式**
  - ✨ 同一次呼叫合并为一条记录
  - ✨ 新增呼叫状态字段 (call_state)
  - ✨ 新增各阶段时间戳 (invite_time, answer_time, bye_time)
  - ✨ 简化记录类型 (CALL, REGISTER, MESSAGE, OPTIONS)
  - ✨ 优化字段结构，更易于分析和计费
  
- v1.0 (2025-10-27): 初始版本，支持基本的 CDR 记录和查询功能

