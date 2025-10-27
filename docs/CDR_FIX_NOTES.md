# CDR 重复记录问题修复说明

## 🐛 问题描述

**现象：** 同一个 Call-ID 产生了多条 480 错误的 CDR 记录

**案例：**
```
Call-ID: EdO1fgZDCLabvQcN5pashw..
- 第1条: 20:17:20 CALL (FAILED) - 有主被叫信息 ✓
- 第2条: 20:19:21 (FAILED) - 空记录 ❌
- 第3条: 20:19:22 (FAILED) - 空记录 ❌
- ...
- 第11条: 20:19:52 (FAILED) - 空记录 ❌
```

## 🔍 根本原因

### 问题流程

1. **20:17:20** - 用户 1001 呼叫 1002，发送 INVITE
2. **20:17:21** - 收到 180 Ringing（振铃中）
3. **20:18:21** - 收到 180 Ringing（重传）
4. **20:19:08** - Timer H 清理 INVITE branch（60秒超时）
5. **20:19:21** - 被叫端开始发送 480 Temporarily Unavailable
6. **20:19:21-20:19:52** - 被叫端按 SIP 协议重传 480 响应（每隔几秒重传）
7. **问题：每次收到 480 响应都记录了新的 CDR** ❌

### 代码问题

**旧代码（run.py 920-937 行）：**
```python
# 每次收到 4xx/5xx/6xx 响应都记录 CDR
elif status_code.startswith(('4', '5', '6')):
    cdr.record_call_fail(...)  # 没有检查是否已记录过！
```

**为什么会重复：**
- 第一次记录 480 时，`cdr.record_call_fail()` 会调用 `flush_record(call_id)`
- 后续的 480 重传会创建新的记录（因为缓存已被清空）
- 但这些新记录没有主被叫信息（因为不在 record_cache 中）

## ✅ 修复方案

### 核心思路

**只在第一次收到最终响应时记录 CDR，忽略后续重传**

### 实现方法

```python
# 1. 使用 DIALOGS 字典判断是否是第一次收到响应
need_cleanup = False
if status_code in ("486", "487", "488", "600", "603", "604"):
    if call_id in DIALOGS:
        need_cleanup = True  # 第一次收到，需要记录 CDR
    # 清理 DIALOGS
    if call_id in DIALOGS:
        del DIALOGS[call_id]

# 2. 只在第一次清理时记录 CDR
if need_cleanup:
    cdr.record_call_fail(...)  # 只记录一次 ✓

# 3. 对于其他 4xx/5xx 响应（如 480）
if status_code.startswith(('4', '5', '6')):
    if call_id in DIALOGS:  # 仅当还在 DIALOGS 中才记录
        cdr.record_call_fail(...)
        # 立即清理，避免重复
        del DIALOGS[call_id]
```

### 关键改进

1. ✅ **状态检查**：通过 `call_id in DIALOGS` 判断是否已记录
2. ✅ **立即清理**：记录 CDR 后立即删除 DIALOGS 条目
3. ✅ **去重保证**：同一个 Call-ID 只会记录一次 CDR

## 📊 修复效果

### 修复前
```
同一个 Call-ID → 10+ 条 CDR 记录
- 第1条有完整信息
- 其他9条都是空记录（重传导致）
```

### 修复后
```
同一个 Call-ID → 1 条 CDR 记录
- 包含完整的主被叫信息
- 准确的状态码和时间
- 后续重传被自动忽略
```

## 🧪 测试验证

### 测试场景

1. **正常呼叫** - INVITE → 200 OK → BYE
   - ✅ 应产生 1 条 CALL (ENDED) 记录

2. **用户拒接** - INVITE → 486 Busy Here
   - ✅ 应产生 1 条 CALL (FAILED) 记录
   - ✅ 即使 486 重传多次，也只记录 1 条

3. **超时无应答** - INVITE → 480 Temporarily Unavailable
   - ✅ 应产生 1 条 CALL (FAILED) 记录
   - ✅ 即使 480 重传多次，也只记录 1 条

4. **用户取消** - INVITE → CANCEL → 487
   - ✅ 应产生 1 条 CALL (CANCELLED) 记录

### 验证步骤

```bash
# 1. 清理旧 CDR
rm -f CDR/2025-10-27/cdr_2025-10-27.csv

# 2. 重启服务器
python3 run.py

# 3. 进行测试呼叫（让被叫不接听，等待超时）

# 4. 查看 CDR
python3 cdr_viewer.py recent --limit 20

# 5. 检查同一个 Call-ID 是否只有 1 条记录
python3 cdr_viewer.py stats
```

### 预期结果

```
✓ 每个 Call-ID 只有 1 条 CDR 记录
✓ 记录包含完整信息（主叫、被叫、状态码等）
✓ 统计数据准确（不会因为重传而虚高）
```

## 📝 相关文件

- `run.py` (行 910-964) - 修复了 CDR 重复记录逻辑
- `sipcore/cdr.py` - CDR 核心模块（无需修改）
- `cdr_viewer.py` - CDR 查看工具（无需修改）

## 🎯 总结

**问题：** SIP 协议的响应重传机制导致同一个呼叫产生多条 CDR 记录

**原因：** 每次收到响应都记录 CDR，没有去重检查

**解决：** 通过 DIALOGS 字典判断是否已记录，确保同一个 Call-ID 只记录一次

**效果：** CDR 记录准确、简洁，便于计费和统计分析

---

**修复日期：** 2025-10-27  
**版本：** v2.1

