# 更新日志

## [2.0.0] - 2025-10-27

### 新增功能 ✨

#### CDR 话单系统
- ✅ 自动生成 CDR 记录（呼叫、注册、短信等）
- ✅ 智能合并机制（同一通话/注册的多条记录合并为一条）
- ✅ 防重复记录机制（避免重传导致的重复）
- ✅ 按日期自动归档到 `CDR/` 目录
- ✅ 命令行查看工具 `cdr_viewer.py`

**支持的 CDR 类型：**
- `CALL_START` - 呼叫发起
- `CALL_ANSWER` - 呼叫接听
- `CALL_END` - 正常挂断
- `CALL_FAIL` - 呼叫失败
- `CALL_CANCEL` - 呼叫取消
- `REGISTER` - 用户注册
- `UNREGISTER` - 用户注销
- `MESSAGE` - 短信记录

#### Web 配置界面
- ✅ 零依赖 Web 管理界面（端口 8888）
- ✅ 实时监控（服务器状态、在线用户、活跃呼叫）
- ✅ 动态配置支持（部分参数可运行时修改）
- ✅ 完全中文化界面
- ✅ 响应式设计

**可配置参数：**
- `LOG_LEVEL` - 日志级别（立即生效）
- `SERVER_PORT` - 服务器端口（重启生效）
- `MAX_FORWARDS` - 最大转发次数（立即生效）
- `REGISTRATION_EXPIRES` - 注册过期时间（立即生效）

#### 配置管理系统
- ✅ `config_manager.py` - 动态配置管理
- ✅ `config.json` - 配置持久化存储
- ✅ 配置热更新（部分参数）

---

### 改进 🔧

#### CDR 系统优化
- ✅ **智能合并**：同一 Call-ID 的多条记录自动合并
  - 呼叫：INVITE + 200 OK + BYE → 单条记录（包含完整时间线）
  - 注册：多次 REGISTER → 单条记录（显示最终状态）
- ✅ **去重机制**：防止重传导致的重复 CDR
  - 使用 `flushed_records` 跟踪已写入记录
  - BYE/CANCEL 只在首次收到时记录
  - MESSAGE 使用 `Call-ID + CSeq` 唯一标识

#### 网络错误处理
- ✅ **优雅降级**：网络不可达时返回合适的 SIP 错误码
  - INVITE/MESSAGE: 480 Temporarily Unavailable
  - BYE: 408 Request Timeout
  - 其他: 503 Service Unavailable
- ✅ **日志优化**：网络错误记为 WARNING 而非 ERROR
- ✅ **自动清理**：网络错误时清理 DIALOGS 防止重复

#### 认证流程优化
- ✅ **401 处理**：不再将 401 Unauthorized 视为注册失败
- ✅ **认证流程**：正确识别 SIP Challenge-Response 流程

---

### 修复 🐛

#### CDR 重复记录修复
- ✅ **问题**：480/486 等失败响应因重传产生多条 CDR
- ✅ **修复**：只在首次收到最终响应时记录 CDR
  - 检查 DIALOGS 是否存在
  - 记录后立即清理 DIALOGS
  - 后续重传不再记录

#### 注册 CDR 修复
- ✅ **问题**：401 被错误记录为注册失败
- ✅ **修复**：移除 401 的 CDR 记录（属于正常认证流程）
- ✅ **问题**：同一 Call-ID 的多次注册产生多条 CDR
- ✅ **修复**：自动合并为单条记录，显示最终状态

#### BYE/CANCEL 去重
- ✅ **问题**：BYE/CANCEL 重传导致重复 CDR
- ✅ **修复**：通过 DIALOGS 检查确保只记录一次

#### MESSAGE 去重
- ✅ **问题**：MESSAGE 请求可能重复记录
- ✅ **修复**：使用 `Call-ID + CSeq` 作为唯一标识

#### LOG_LEVEL 动态修改
- ✅ **问题**：`'SIPLogger' object has no attribute 'setLevel'`
- ✅ **修复**：正确访问底层 `logging.Logger` 对象及其 handlers

---

### 文档 📚

#### 新增文档
- ✅ `README.md` - 全新的主文档（功能总览、快速开始）
- ✅ `docs/INDEX.md` - 文档索引和导航
- ✅ `docs/SIP_CORE_README.md` - SIP 核心实现详解
- ✅ `docs/CDR_README.md` - CDR 系统完整文档
- ✅ `docs/WEB_CONFIG_README.md` - Web 配置界面文档
- ✅ `docs/WEB_CONFIG_EDIT_GUIDE.md` - 配置编辑指南
- ✅ `docs/CDR_DEDUPLICATION.md` - CDR 去重机制说明
- ✅ `docs/NETWORK_ERROR_HANDLING.md` - 网络错误处理说明
- ✅ `docs/CDR_FIX_NOTES.md` - 480 重复记录修复说明
- ✅ `docs/REGISTER_CDR_FIX.md` - 注册 CDR 修复说明
- ✅ `docs/BUG_FIX_LOG_LEVEL.md` - LOG_LEVEL 修复说明
- ✅ `docs/FEATURE_SUMMARY.md` - 功能总结
- ✅ `docs/QUICK_START.md` - 快速开始指南
- ✅ `docs/CONFIG_EDIT_QUICKSTART.md` - 配置编辑快速指南

#### 文档整理
- ✅ 创建 `docs/` 目录统一管理所有文档
- ✅ 分类整理（功能文档、修复说明、快速指南）
- ✅ 创建索引页面便于查找
- ✅ 删除不需要的文档（ngrok 相关）

---

### 工具 🛠️

#### CDR 查看工具
```bash
# 查看最近记录
python cdr_viewer.py --recent 10

# 查看指定日期
python cdr_viewer.py --date 2025-10-27

# 查看呼叫详情
python cdr_viewer.py --call-id abc123...
```

#### Web 管理界面
```bash
# 访问 Web 界面
http://localhost:8888

# API 端点
GET  /api/status          # 服务器状态
GET  /api/config          # 当前配置
GET  /api/config/editable # 可编辑配置
POST /api/config/update   # 更新配置
```

---

### 技术债务 ⚠️

#### 待优化项
- ⏳ CDR 归档压缩（历史数据自动压缩）
- ⏳ Web 界面认证（当前无访问控制）
- ⏳ 配置热更新扩展（更多参数支持）
- ⏳ CDR 统计报表（呼叫统计、失败分析）

#### 已知限制
- ⚠️ 无 TLS/SRTP 支持
- ⚠️ 无访问控制列表
- ⚠️ 单线程异步架构（高并发场景需优化）

---

## [1.0.0] - 2025-10-26

### 初始版本

#### SIP 核心功能
- ✅ RFC 3261 基础实现
- ✅ REGISTER 用户注册
- ✅ INVITE 呼叫建立
- ✅ ACK 确认（2xx 和非 2xx）
- ✅ BYE 呼叫终止
- ✅ CANCEL 呼叫取消
- ✅ MESSAGE 即时消息
- ✅ OPTIONS 能力查询

#### 路由功能
- ✅ 初始请求路由
- ✅ In-dialog 请求路由
- ✅ Record-Route 处理
- ✅ Via 头处理
- ✅ 环路检测

#### NAT 支持
- ✅ Contact 地址修正
- ✅ received/rport 参数
- ✅ 本机测试模式
- ✅ 局域网模式

#### 日志系统
- ✅ 彩色控制台输出
- ✅ 文件日志记录
- ✅ SIP 专用日志方法（RX/TX/FWD/DROP）
- ✅ 多级别日志（DEBUG/INFO/WARNING/ERROR）

#### 定时器机制
- ✅ RFC 3261 标准定时器
- ✅ 对话超时清理
- ✅ 待处理请求清理
- ✅ 注册绑定过期清理

---

## 升级指南

### 从 1.0.0 升级到 2.0.0

1. **备份数据**
```bash
cp config.json config.json.backup
```

2. **安装依赖**（无新依赖）
```bash
pip install -r requirements.txt
```

3. **启动服务**
```bash
python run.py
```

4. **访问 Web 界面**
```bash
http://localhost:8888
```

5. **检查 CDR**
```bash
python cdr_viewer.py --recent 10
```

### 配置迁移

**无需手动配置迁移**，服务器会自动：
- 创建 `config.json`（如不存在）
- 创建 `CDR/` 目录
- 初始化 Web 服务（端口 8888）

---

## 未来计划 🚀

### v2.1.0（计划中）
- 📊 CDR 统计报表
- 📈 实时监控图表
- 🔐 Web 界面认证
- 📦 CDR 自动归档压缩

### v2.2.0（计划中）
- 🔒 TLS/SRTP 支持
- 🛡️ 访问控制列表
- 🚀 性能优化（多进程支持）
- 📱 移动端 APP

---

## 贡献者 👥

感谢所有为项目做出贡献的人！

---

## 许可证 📜

MIT License

---

**项目主页**: [IMS SIP Server](.)  
**文档**: [docs/INDEX.md](docs/INDEX.md)  
**问题反馈**: Issues  

---

_保持更新，享受 SIP！_ 🎉

