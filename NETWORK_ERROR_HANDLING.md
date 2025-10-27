# 网络错误处理优化说明

## 🔍 错误现象

```
2025-10-27 20:37:47 [ERROR] UDP server error: [Errno 65] No route to host
```

## 📊 问题分析

### 错误场景

**实际情况（从日志分析）：**
```
1. 用户 1001 (192.168.8.129) 发送 BYE 给用户 1002
2. 服务器尝试转发 BYE 到 192.168.8.120:41303
3. ❌ [Errno 65] No route to host
4. 原因：用户 1002 已经下线/断网，但没有正常注销
```

### Errno 65 说明

**平台差异：**
- **macOS/BSD**: `errno 65` = No route to host
- **Linux**: `errno 113` = No route to host
- **通用**: `errno 101` = Network is unreachable

**含义：**
- 目标主机不可达（可能已下线、断网、防火墙阻止等）
- 这是**正常的网络状况**，不是服务器错误

### 常见原因

1. ✅ **客户端异常退出**
   - 直接关闭客户端（没有发送 UNREGISTER）
   - 程序崩溃
   - 强制结束进程

2. ✅ **网络故障**
   - 客户端断网
   - WiFi 断开
   - 网线拔出

3. ✅ **设备关机**
   - 电脑关机/休眠
   - 手机锁屏/后台清理

4. ✅ **防火墙/路由**
   - 防火墙规则变化
   - 路由表更新
   - NAT 超时

## ✅ 改进方案

### 改进 1: 优化日志级别

**修改文件：** `sipcore/transport_udp.py`

**改进前：**
```python
def error_received(self, exc):
    log.error(f"UDP server error: {exc}")
```

**问题：** 所有 UDP 错误都记录为 ERROR，但目标不可达是正常网络状况

**改进后：**
```python
def error_received(self, exc):
    if hasattr(exc, 'errno') and exc.errno in (65, 113, 101):
        # 目标不可达 - 正常网络状况，使用 WARNING
        log.warning(f"UDP: Target unreachable - {exc}")
    else:
        # 其他错误 - 真正的服务器错误，使用 ERROR
        log.error(f"UDP server error: {exc}")
```

**效果：**
- ✅ 日志级别更准确（WARNING vs ERROR）
- ✅ 易于区分正常网络问题和真正的错误
- ✅ 监控告警不会被误触发

### 改进 2: 增强错误处理和响应

**修改文件：** `run.py` (763-793 行)

**改进前：**
```python
except Exception as e:
    resp = _make_response(msg, 502, "Bad Gateway")
    transport.sendto(resp.to_bytes(), addr)
```

**问题：** 所有异常都返回 502，不够具体

**改进后：**
```python
except OSError as e:
    if e.errno in (65, 113, 101):
        # 目标不可达 - 返回 480 或 408
        if method in ("INVITE", "MESSAGE", ...):
            resp = _make_response(msg, 480, "Temporarily Unavailable")
        elif method == "BYE":
            resp = _make_response(msg, 408, "Request Timeout")
        transport.sendto(resp.to_bytes(), addr)
    else:
        # 其他网络错误 - 返回 503
        resp = _make_response(msg, 503, "Service Unavailable")
        transport.sendto(resp.to_bytes(), addr)
except Exception as e:
    # 其他异常 - 返回 502
    resp = _make_response(msg, 502, "Bad Gateway")
    transport.sendto(resp.to_bytes(), addr)
```

**效果：**
- ✅ 返回更准确的 SIP 状态码
- ✅ 客户端能够正确处理错误
- ✅ 符合 SIP 协议规范

### SIP 状态码选择

| 场景 | 状态码 | 说明 |
|------|--------|------|
| INVITE 失败（目标不可达） | 480 Temporarily Unavailable | 标准的"对方不可用"响应 |
| BYE 失败（目标不可达） | 408 Request Timeout | 请求超时，对方无响应 |
| 其他网络错误 | 503 Service Unavailable | 服务暂时不可用 |
| 代码异常 | 502 Bad Gateway | 网关错误 |

## 📊 效果对比

### 改进前

**日志输出：**
```
2025-10-27 20:37:47 [ERROR] UDP server error: [Errno 65] No route to host
2025-10-27 20:37:47 [INFO] [FWD] BYE -> 192.168.8.120:41303
```

**客户端收到：**
```
502 Bad Gateway (不够准确)
```

**问题：**
- ❌ 日志级别误导（ERROR 应该是真正的错误）
- ❌ 状态码不够具体
- ❌ 没有清理失效的注册信息

### 改进后

**日志输出：**
```
2025-10-27 20:37:47 [WARNING] UDP: Target unreachable - [Errno 65] No route to host
2025-10-27 20:37:47 [WARNING] [NETWORK] Target unreachable 192.168.8.120:41303
2025-10-27 20:37:47 [INFO] [TX] 192.168.8.129:57446 <- 408 Request Timeout
```

**客户端收到：**
```
408 Request Timeout (BYE 失败的标准响应)
```

**效果：**
- ✅ 日志级别准确（WARNING = 预期的网络问题）
- ✅ 状态码符合 SIP 标准
- ✅ 客户端能正确处理

## 🔧 进一步优化建议

### 1. 自动清理失效注册

**场景：** 当检测到用户不可达时，自动清理其注册信息

```python
# 在检测到目标不可达时
if e.errno in (65, 113, 101):
    # 清理失效的注册信息
    aor = _aor_from_to(msg.get("to"))
    if aor in REG_BINDINGS:
        # 标记为不可达或直接删除
        del REG_BINDINGS[aor]
        log.info(f"[CLEANUP] Removed unreachable binding: {aor}")
```

### 2. 添加健康检查

**场景：** 定期 ping 注册用户，清理不在线的

```python
async def health_check():
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        for aor, bindings in REG_BINDINGS.items():
            # 发送 OPTIONS 检查
            # 如果失败，标记或清理
```

### 3. 重试机制

**场景：** 对于重要请求（如 BYE），可以尝试备用地址

```python
# 如果主地址失败，尝试用户的其他注册地址
if e.errno in (65, 113, 101) and method == "BYE":
    # 尝试其他绑定
    for binding in REG_BINDINGS.get(aor, [])[1:]:
        try:
            transport.sendto(msg.to_bytes(), binding['addr'])
            break
        except:
            continue
```

## 📝 最佳实践

### 1. 客户端行为

**应该做：**
- ✅ 正常退出时发送 UNREGISTER (Expires: 0)
- ✅ 设置合理的注册过期时间 (60-3600秒)
- ✅ 定期刷新注册

**不应该做：**
- ❌ 直接关闭应用不注销
- ❌ 设置过长的过期时间
- ❌ 断网后不重新注册

### 2. 服务器行为

**应该做：**
- ✅ 区分网络错误和程序错误
- ✅ 返回准确的 SIP 状态码
- ✅ 定期清理过期注册
- ✅ 记录详细的调试日志

**不应该做：**
- ❌ 把所有错误都记录为 ERROR
- ❌ 返回不准确的状态码
- ❌ 保留失效的注册信息

## 🎯 总结

### 核心改进

1. ✅ **日志级别优化** - WARNING vs ERROR，更准确
2. ✅ **状态码优化** - 480/408/503/502，更具体
3. ✅ **错误分类** - 网络错误 vs 程序错误，易排查

### 影响范围

- **transport_udp.py** - 优化 UDP 错误日志
- **run.py** - 增强请求转发的错误处理
- **日志输出** - 更清晰的错误信息

### 兼容性

- ✅ 向后兼容：只是改进错误处理
- ✅ 客户端友好：返回标准 SIP 状态码
- ✅ 运维友好：日志更易于分析和监控

---

**修复日期：** 2025-10-27  
**版本：** v2.3

