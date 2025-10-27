# 工具脚本

本目录包含各种实用工具脚本。

## 📊 CDR 查看工具

### cdr_viewer.py

CDR 话单查看和分析工具。

**使用方法：**

```bash
# 查看最近 10 条记录
python tools/cdr_viewer.py --recent 10

# 查看指定日期的话单
python tools/cdr_viewer.py --date 2025-10-27

# 查看特定呼叫详情
python tools/cdr_viewer.py --call-id abc123...

# 导出今日呼叫记录
python tools/cdr_viewer.py --export-today CALL

# 导出今日短信记录
python tools/cdr_viewer.py --export-today MESSAGE
```

## 🧪 测试脚本

### test_cdr.py

CDR 基础功能测试脚本。

**使用方法：**
```bash
python tools/test_cdr.py
```

### test_cdr_merged.py

CDR 合并功能测试脚本。

**使用方法：**
```bash
python tools/test_cdr_merged.py
```

---

**注意**：运行工具时请从项目根目录执行，使用 `python tools/xxx.py` 格式。

