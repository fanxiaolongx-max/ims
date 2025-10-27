# 导出数据

本目录存放通过 `cdr_viewer.py` 工具导出的 CDR 数据文件。

## 📁 文件说明

导出的文件按照以下命名规则：

```
cdr_export_<日期>_<类型>.csv
```

**示例：**
- `cdr_export_today_CALL.csv` - 今日呼叫记录
- `cdr_export_today_MESSAGE.csv` - 今日短信记录
- `cdr_export_2025-10-27_CALL.csv` - 指定日期呼叫记录

## 📊 导出 CDR

### 导出今日数据

```bash
# 导出今日所有呼叫记录
python tools/cdr_viewer.py --export-today CALL

# 导出今日所有短信记录
python tools/cdr_viewer.py --export-today MESSAGE

# 导出今日所有注册记录
python tools/cdr_viewer.py --export-today REGISTER
```

### 导出指定日期

```bash
# 导出指定日期的呼叫记录
python tools/cdr_viewer.py --date 2025-10-27 --export CALL

# 导出指定日期的短信记录
python tools/cdr_viewer.py --date 2025-10-27 --export MESSAGE
```

## 📄 CSV 格式

导出的 CSV 文件包含以下字段（根据记录类型不同）：

### 呼叫记录（CALL）

| 字段 | 说明 |
|-----|------|
| record_type | 记录类型（CALL_START/CALL_ANSWER/CALL_END等）|
| call_id | 呼叫 ID |
| start_time | 开始时间 |
| end_time | 结束时间 |
| caller_uri | 主叫 URI |
| callee_uri | 被叫 URI |
| call_state | 呼叫状态 |
| duration | 通话时长（秒）|

### 短信记录（MESSAGE）

| 字段 | 说明 |
|-----|------|
| record_type | 记录类型（MESSAGE）|
| call_id | 消息 ID |
| timestamp | 时间戳 |
| caller_uri | 发送方 URI |
| callee_uri | 接收方 URI |
| message_body | 消息内容 |

### 注册记录（REGISTER）

| 字段 | 说明 |
|-----|------|
| record_type | 记录类型（REGISTER/UNREGISTER）|
| call_id | 注册 Call-ID |
| timestamp | 时间戳 |
| user_uri | 用户 URI |
| contact_uri | Contact 地址 |
| expires | 过期时间 |
| register_state | 注册状态 |

## 💡 使用场景

### 数据分析
```bash
# 使用 Excel/LibreOffice 打开 CSV
libreoffice export/cdr_export_today_CALL.csv

# 使用 Python pandas 分析
python3 << EOF
import pandas as pd
df = pd.read_csv('export/cdr_export_today_CALL.csv')
print(df.describe())
print(df['call_state'].value_counts())
EOF
```

### 计费对账
```bash
# 统计今日呼叫总时长
awk -F',' 'NR>1 {sum+=$8} END {print sum " seconds"}' export/cdr_export_today_CALL.csv

# 统计今日短信数量
wc -l export/cdr_export_today_MESSAGE.csv
```

### 导入其他系统
```bash
# 导入到 MySQL
mysql -u user -p database << EOF
LOAD DATA LOCAL INFILE 'export/cdr_export_today_CALL.csv'
INTO TABLE call_records
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
EOF
```

## 🗑️ 清理导出文件

### 手动清理
```bash
# 删除所有导出文件
rm export/*.csv

# 删除7天前的文件
find export/ -name "*.csv" -mtime +7 -delete
```

### 自动清理脚本
```bash
#!/bin/bash
# cleanup_exports.sh
cd /path/to/ims/export
find . -name "cdr_export_*.csv" -mtime +30 -delete
echo "清理完成：$(date)"
```

## 📚 相关文档

- [CDR 系统文档](../docs/CDR_README.md)
- [cdr_viewer 工具说明](../tools/README.md)

---

**注意**：
- CSV 文件使用 UTF-8 编码
- 定期清理旧的导出文件以节省空间
- 敏感数据请妥善保管

