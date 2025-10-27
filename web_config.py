"""
Web 配置界面模块
展示 SIP 服务器的所有可配置参数
使用 Python 内置 http.server，无需额外依赖
"""
import threading
import webbrowser
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IMS SIP 服务器 - 配置面板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            animation: fadeInDown 0.8s ease;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .status-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 10px;
            animation: pulse 2s infinite;
        }
        
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            animation: fadeInUp 0.8s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .card-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        
        .config-item {
            margin-bottom: 15px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .config-label {
            font-weight: 600;
            color: #4b5563;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .config-value {
            font-family: 'Monaco', 'Courier New', monospace;
            color: #1f2937;
            font-size: 1.1em;
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            margin-top: 5px;
            border: 1px solid #e5e7eb;
            word-break: break-all;
        }
        
        .config-desc {
            color: #6b7280;
            font-size: 0.85em;
            margin-top: 5px;
            line-height: 1.5;
        }
        
        .users-list {
            display: grid;
            gap: 10px;
        }
        
        .user-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #e5e7eb;
        }
        
        .user-name {
            font-weight: 600;
            color: #667eea;
        }
        
        .user-pass {
            font-family: monospace;
            color: #6b7280;
        }
        
        .network-item {
            background: white;
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 8px;
            border: 1px solid #e5e7eb;
            font-family: monospace;
            color: #1f2937;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 2px;
        }
        
        .badge-success {
            background: #d1fae5;
            color: #065f46;
        }
        
        .badge-warning {
            background: #fef3c7;
            color: #92400e;
        }
        
        .badge-info {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }
        
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.8;
            }
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .cards-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 IMS SIP 服务器</h1>
            <p>配置参数面板</p>
            <span class="status-badge">● 服务运行中</span>
        </div>
        
        <div class="cards-grid">
            <!-- 基础配置 -->
            <div class="card">
                <div class="card-title">🌐 基础配置</div>
                
                <div class="config-item">
                    <div class="config-label">服务器 IP 地址</div>
                    <div class="config-value" id="server-ip"></div>
                    <div class="config-desc">SIP 服务器监听的 IP 地址</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">服务器端口</div>
                    <div class="config-value" id="server-port"></div>
                    <div class="config-desc">SIP 信令监听端口（标准端口为 5060）</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">服务器 URI</div>
                    <div class="config-value" id="server-uri"></div>
                    <div class="config-desc">用于 Record-Route 头的完整 SIP URI</div>
                </div>
            </div>
            
            <!-- SIP 能力 -->
            <div class="card">
                <div class="card-title">📡 SIP 协议能力</div>
                
                <div class="config-item">
                    <div class="config-label">支持的方法</div>
                    <div class="config-value" id="sip-methods"></div>
                    <div class="config-desc">服务器支持的所有 SIP 方法</div>
                </div>
            </div>
            
            <!-- 网络配置 -->
            <div class="card">
                <div class="card-title">🔧 网络环境配置</div>
                
                <div class="config-item">
                    <div class="config-label">本地网络地址</div>
                    <div class="config-desc" style="margin-bottom: 10px;">
                        不需要地址转换的本地/局域网地址列表
                    </div>
                    <div id="local-networks"></div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">强制本地地址模式</div>
                    <div class="config-value" id="force-local"></div>
                    <div class="config-desc">
                        • True: 单机测试模式，所有地址强制使用本地<br>
                        • False: 真实网络模式，支持多机互联
                    </div>
                </div>
            </div>
            
            <!-- 用户认证 -->
            <div class="card">
                <div class="card-title">👥 用户认证</div>
                
                <div class="config-item">
                    <div class="config-label">注册用户列表</div>
                    <div class="config-desc" style="margin-bottom: 10px;">
                        可以注册到服务器的用户账号和密码
                    </div>
                    <div class="users-list" id="users-list"></div>
                </div>
            </div>
            
            <!-- CDR 配置 -->
            <div class="card">
                <div class="card-title">📊 CDR (话单记录)</div>
                
                <div class="config-item">
                    <div class="config-label">CDR 存储目录</div>
                    <div class="config-value">CDR/</div>
                    <div class="config-desc">话单记录自动按日期存储到此目录</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">记录合并模式</div>
                    <div class="config-value">
                        <span class="badge badge-success">✓ 启用</span>
                    </div>
                    <div class="config-desc">
                        同一呼叫/注册的多条记录自动合并为一条，避免重复
                    </div>
                </div>
            </div>
            
            <!-- 日志配置 -->
            <div class="card">
                <div class="card-title">📝 日志配置</div>
                
                <div class="config-item">
                    <div class="config-label">日志级别</div>
                    <div class="config-value">
                        <span class="badge badge-info">DEBUG</span>
                    </div>
                    <div class="config-desc">记录详细的调试信息</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">日志文件</div>
                    <div class="config-value">ims-sip-server.log</div>
                    <div class="config-desc">所有 SIP 消息和系统日志的输出文件</div>
                </div>
            </div>
            
            <!-- 高级配置 -->
            <div class="card">
                <div class="card-title">⚙️ 高级配置</div>
                
                <div class="config-item">
                    <div class="config-label">默认注册过期时间</div>
                    <div class="config-value">3600 秒 (1 小时)</div>
                    <div class="config-desc">客户端未指定时的默认注册有效期</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">SIP 定时器</div>
                    <div class="config-value">
                        <span class="badge badge-success">✓ 启用</span>
                    </div>
                    <div class="config-desc">
                        • INVITE 事务超时清理<br>
                        • 注册绑定过期清理<br>
                        • CDR 缓存定期清理
                    </div>
                </div>
            </div>
            
            <!-- 运行状态 -->
            <div class="card">
                <div class="card-title">📈 运行状态</div>
                
                <div class="config-item">
                    <div class="config-label">当前注册用户</div>
                    <div class="config-value" id="registered-users"></div>
                    <div class="config-desc">已注册用户数 / 总用户数</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">活动对话</div>
                    <div class="config-value" id="active-dialogs"></div>
                    <div class="config-desc">当前正在进行的通话数量</div>
                </div>
                
                <div class="config-item">
                    <div class="config-label">待处理请求</div>
                    <div class="config-value" id="pending-requests"></div>
                    <div class="config-desc">等待响应的 SIP 请求数量</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>IMS SIP Server v2.4 | Powered by Python</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                访问地址: <strong>http://localhost:8080</strong>
            </p>
        </div>
    </div>
    
    <script>
        // 加载配置数据
        fetch('/api/config')
            .then(response => response.json())
            .then(data => {
                // 基础配置
                document.getElementById('server-ip').textContent = data.SERVER_IP;
                document.getElementById('server-port').textContent = data.SERVER_PORT;
                document.getElementById('server-uri').textContent = data.SERVER_URI;
                
                // SIP 方法
                const methods = data.ALLOW.split(', ');
                document.getElementById('sip-methods').innerHTML = methods.map(m => 
                    `<span class="badge badge-info">${m}</span>`
                ).join(' ');
                
                // 本地网络
                document.getElementById('local-networks').innerHTML = data.LOCAL_NETWORKS.map(n =>
                    `<div class="network-item">${n}</div>`
                ).join('');
                
                // 强制本地模式
                const forceLocal = data.FORCE_LOCAL_ADDR;
                document.getElementById('force-local').innerHTML = forceLocal
                    ? '<span class="badge badge-warning">✓ 启用（单机测试模式）</span>'
                    : '<span class="badge badge-success">✗ 禁用（真实网络模式）</span>';
                
                // 用户列表
                const users = Object.entries(data.USERS).map(([user, pass]) =>
                    `<div class="user-item">
                        <span class="user-name">📱 ${user}</span>
                        <span class="user-pass">🔑 ${pass}</span>
                    </div>`
                ).join('');
                document.getElementById('users-list').innerHTML = users;
                
                // 运行状态
                document.getElementById('registered-users').textContent = 
                    `${data.status.registered_users} / ${Object.keys(data.USERS).length}`;
                document.getElementById('active-dialogs').textContent = data.status.active_dialogs;
                document.getElementById('pending-requests').textContent = data.status.pending_requests;
            })
            .catch(error => console.error('Error loading config:', error));
    </script>
</body>
</html>
"""

class ConfigHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        """禁用默认日志输出"""
        pass
    
    def do_POST(self):
        """处理 POST 请求（配置修改）"""
        if self.path == '/api/config/update':
            try:
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                # 导入配置管理器
                from config_manager import apply_config_change
                
                key = data.get('key')
                value = data.get('value')
                
                if not key:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    response = {'success': False, 'message': '缺少配置项名称'}
                    self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                    return
                
                # 应用配置更改
                success, message = apply_config_change(key, value)
                
                self.send_response(200 if success else 400)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    'success': success,
                    'message': message,
                    'key': key,
                    'value': value
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                response = {'success': False, 'message': f'服务器错误: {str(e)}'}
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """处理 OPTIONS 请求（CORS 预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/':
            # 返回 HTML 页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
        elif self.path == '/api/config':
            # 返回配置 JSON
            try:
                from run import (
                    SERVER_IP, SERVER_PORT, SERVER_URI, ALLOW,
                    LOCAL_NETWORKS, FORCE_LOCAL_ADDR, USERS,
                    REG_BINDINGS, DIALOGS, PENDING_REQUESTS
                )
                
                config = {
                    'SERVER_IP': SERVER_IP,
                    'SERVER_PORT': SERVER_PORT,
                    'SERVER_URI': SERVER_URI,
                    'ALLOW': ALLOW,
                    'LOCAL_NETWORKS': LOCAL_NETWORKS,
                    'FORCE_LOCAL_ADDR': FORCE_LOCAL_ADDR,
                    'USERS': USERS,
                    'status': {
                        'registered_users': len(REG_BINDINGS),
                        'active_dialogs': len(DIALOGS),
                        'pending_requests': len(PENDING_REQUESTS)
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(config, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
        
        elif self.path == '/api/config/editable':
            # 返回可编辑的配置项定义
            try:
                from config_manager import get_editable_configs
                
                editable = get_editable_configs()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(editable, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


# Web 服务器配置
WEB_HOST = '127.0.0.1'
WEB_PORT = 8080

def start_web_server():
    """启动 Web 服务器"""
    server = HTTPServer((WEB_HOST, WEB_PORT), ConfigHandler)
    server.serve_forever()

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)  # 等待服务器启动
    webbrowser.open(f'http://{WEB_HOST}:{WEB_PORT}')

def init_web_interface():
    """初始化 Web 界面"""
    # 启动 Web 服务器线程
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # 启动浏览器线程
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    print(f"\n{'='*60}")
    print(f"🌐 Web 配置面板已启动")
    print(f"📍 访问地址: http://{WEB_HOST}:{WEB_PORT}")
    print(f"{'='*60}\n")
    
    return web_thread

if __name__ == '__main__':
    # 测试模式
    init_web_interface()
    input("按 Enter 键退出...")
