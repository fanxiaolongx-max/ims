# REGISTER CDR 记录优化

## 🐛 修复的问题

### 问题 1: 401 被错误记录为注册失败

**现象：**
```
1. [20:23:49] REGISTER (SUCCESS)
   Call-ID: uur-8BZb43QQdP-NfX98CA..
   
2. [20:23:49] REGISTER (FAILED)  ❌ 错误！
   Call-ID: uur-8BZb43QQdP-NfX98CA..
   状态: 401 Unauthorized
```

**问题分析：**

401 Unauthorized 是**正常的 SIP 认证挑战流程**，不是失败！

**标准的 SIP REGISTER 流程：**
```
步骤 1: 客户端发送 REGISTER（无认证信息）
        ↓
步骤 2: 服务器返回 401 Unauthorized（认证挑战）✅ 正常流程
        ↓
步骤 3: 客户端重新发送 REGISTER（带认证信息）
        ↓
步骤 4: 服务器返回 200 OK（注册成功）✅ 最终结果
```

**旧代码问题：**
- 在步骤 2 返回 401 时，如果请求包含 Authorization 头，就记录为失败
- 这导致正常的认证流程被误判为失败

### 问题 2: 同一次注册产生多条 CDR

**现象：**
- 同一个 Call-ID 产生了 2 条记录（401 + 200）
- 实际上这是同一次注册的不同阶段

**期望：**
- 同一个 Call-ID 只产生 1 条记录
- 只记录最终结果（成功或真正的失败）

## ✅ 修复方案

### 修复 1: 移除 401 的失败记录

**修改文件：** `run.py` (255-262 行)

**旧代码：**
```python
if not check_digest(msg, USERS):
    resp = make_401(msg)
    transport.sendto(resp.to_bytes(), addr)
    log.tx(addr, resp.start_line, extra="Auth failed")
    
    # 问题：记录 401 为失败
    if msg.get("authorization"):
        cdr.record_register(..., success=False, status_code=401)
    return
```

**新代码：**
```python
if not check_digest(msg, USERS):
    resp = make_401(msg)
    transport.sendto(resp.to_bytes(), addr)
    log.tx(addr, resp.start_line, extra="Auth failed")
    
    # ✓ 401 是正常认证流程，不记录
    return
```

### 修复 2: 注册使用合并模式

**修改文件：** `sipcore/cdr.py` (277-301 行)

**旧代码：**
```python
def record_register(...):
    # 问题：每次调用都立即写入新记录
    self.write_record(
        record_type="REGISTER",
        call_state=call_state,
        ...
    )
```

**新代码：**
```python
def record_register(...):
    # ✓ 使用合并模式，同一个 call-id 只保留最终结果
    self._update_or_create_record(
        call_id=call_id,
        record_type="REGISTER",
        call_state=call_state,
        ...
    )
    
    # 注册完成，立即写入文件
    self.flush_record(call_id)
```

## 📊 修复效果

### 修复前

**SIP 流程：**
```
1. REGISTER (无认证) → 401 (不记录)
2. REGISTER (有认证) → 200 OK (记录成功)
   但如果前面有认证失败，会记录失败！
```

**CDR 记录：**
```
记录 1: REGISTER (FAILED) - 401 Unauthorized  ❌
记录 2: REGISTER (SUCCESS) - 200 OK           ✓
总计：2 条记录（包含错误的失败记录）
```

### 修复后

**SIP 流程：**
```
1. REGISTER (无认证) → 401 (不记录) ✓
2. REGISTER (有认证) → 200 OK (记录成功) ✓
```

**CDR 记录：**
```
记录 1: REGISTER (SUCCESS) - 200 OK           ✓
总计：1 条记录（只记录最终成功结果）
```

## 🎯 合并模式的好处

### 对于注册

**场景：** 同一个 Call-ID 的多次注册尝试

```
时间 | 动作 | 旧模式 | 新模式
-----|------|--------|--------
T1   | REGISTER (无认证) → 401 | 不记录 | 不记录
T2   | REGISTER (有认证) → 200 | 记录 | 更新缓存
T3   | (写入) | 立即写入 | flush 写入
```

**结果：**
- 旧模式：1 条记录（但可能包含 401 失败记录）
- 新模式：1 条记录（只记录最终成功结果）✅

### 对于呼叫（已有）

**场景：** 同一个 Call-ID 的完整呼叫流程

```
时间 | 动作 | 旧模式 | 新模式
-----|------|--------|--------
T1   | INVITE | 记录 START | 创建记录
T2   | 200 OK | 记录 ANSWER | 更新记录
T3   | BYE | 记录 END | 更新记录 + flush
总计 | - | 3 条记录 | 1 条记录 ✅
```

## 🧪 测试验证

### 测试步骤

```bash
# 1. 清理旧 CDR
rm -f CDR/2025-10-27/cdr_2025-10-27.csv

# 2. 重启服务器
python3 run.py

# 3. 客户端注册（会自动经历 401 → 200 流程）

# 4. 查看 CDR
python3 cdr_viewer.py recent --limit 10
```

### 预期结果

**正常注册：**
```
1. [20:30:00] REGISTER (SUCCESS)
   Call-ID: xxx-xxx-xxx..
   主叫: 1001 (192.168.8.129:57446)
   状态: 200 OK
   过期时间: 3600 秒

✓ 只有 1 条记录
✓ 状态是 SUCCESS
✓ 没有 401 的失败记录
```

**认证失败（真正的失败，密码错误多次）：**
```
这种情况下，客户端会放弃，不会继续发送 REGISTER
所以不会有 CDR 记录（因为从未成功）
或者如果要记录，可以在超时后记录
```

## 📋 总结

### 关键改进

1. ✅ **401 不再被记录为失败** - 认识到这是正常的认证挑战
2. ✅ **注册使用合并模式** - 同一个 Call-ID 只保留最终结果
3. ✅ **CDR 记录更准确** - 避免误判和重复记录

### 影响范围

- **REGISTER** - 现在只记录成功的注册，不记录 401 挑战
- **UNREGISTER** - 也使用合并模式
- **CALL** - 已经使用合并模式（之前已修复）
- **MESSAGE/OPTIONS** - 保持不变

### 兼容性

- ✅ 向后兼容：只是减少了错误记录，不影响正常功能
- ✅ 数据准确性：CDR 记录更符合实际业务语义
- ✅ 统计正确：注册统计不会因为 401 而虚高

---

**修复日期：** 2025-10-27  
**版本：** v2.2

