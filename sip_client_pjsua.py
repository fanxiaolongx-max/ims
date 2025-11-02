#!/usr/bin/env python3
"""
使用 PJSIP (pjsua) 的 SIP 客户端
这是一个成熟的 SIP 库，功能更强大，但需要安装 pjsip-python

安装方法：
1. 安装 PJSIP:
   - macOS: brew install pjsip
   - Linux: apt-get install libpjproject-dev
   - 或从源码编译: http://www.pjsip.org/download.htm

2. 安装 Python 绑定:
   pip install pjsua2

使用方法:
   python3 sip_client_pjsua.py
"""

try:
    import pjsua2 as pj
    PJSUA_AVAILABLE = True
except ImportError:
    PJSUA_AVAILABLE = False
    print("[WARNING] pjsua2 未安装，请使用 sip_client_standalone.py")
    print("[INFO] 安装方法: pip install pjsua2")
    print("[INFO] 注意: pjsua2 需要先安装 PJSIP 库")
    exit(1)

import json
import time
import threading
from typing import Optional, Dict


# ====== 配置 ======
DEFAULT_CONFIG = {
    "server_ip": "192.168.100.8",
    "server_port": 5060,
    "username": "0000",
    "password": "0000",
    "local_port": 10000,
    "media_dir": "media",
    "media_file": "media/default.wav",
}


class SIPAccount(pj.Account):
    """SIP 账户"""
    
    def __init__(self, client):
        pj.Account.__init__(self)
        self.client = client
    
    def onRegState(self):
        """注册状态回调"""
        info = self.getInfo()
        if info.regIsActive:
            print(f"[SIP] ✓ 注册成功")
            self.client.registered = True
        else:
            print(f"[SIP] ✗ 注册失败")
            self.client.registered = False


class SIPCall(pj.Call):
    """SIP 呼叫"""
    
    def __init__(self, account, call_id=-1, client=None):
        pj.Call.__init__(self, account, call_id)
        self.client = client
    
    def onCallState(self):
        """呼叫状态回调"""
        ci = self.getInfo()
        state = ci.stateText
        
        if ci.state == pj.PJSIP_INV_STATE_CALLING:
            print(f"[SIP] 正在呼叫...")
        elif ci.state == pj.PJSIP_INV_STATE_EARLY:
            print(f"[SIP] {ci.lastStatusCode} {state}")
        elif ci.state == pj.PJSIP_INV_STATE_CONNECTING:
            print(f"[SIP] 正在连接...")
        elif ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            print(f"[SIP] ✓ 呼叫已接通")
            # 开始播放媒体
            if self.client:
                self.client.play_media()
        elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            print(f"[SIP] 呼叫已结束")
    
    def onCallMediaState(self):
        """媒体状态回调"""
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO:
                if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    # 媒体已激活，可以播放音频
                    pass


class PJSIPClient:
    """
    使用 PJSIP 的 SIP 客户端
    这是更成熟的实现，支持更多功能
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.lib = None
        self.acc = None
        self.registered = False
        self.current_call = None
        
    def start(self):
        """启动 SIP 库"""
        # 创建 SIP 库实例
        self.lib = pj.Lib()
        
        # 初始化库
        ua_cfg = pj.UAConfig()
        ua_cfg.maxCalls = 100
        
        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig = ua_cfg
        ep_cfg.logConfig.level = 3  # 日志级别
        
        self.lib.init(ep_cfg)
        
        # 创建 UDP 传输
        tcp_cfg = pj.TransportConfig()
        tcp_cfg.port = self.config.get("local_port", 10000)
        
        self.lib.createTransport(pj.PJSIP_TRANSPORT_UDP, tcp_cfg)
        
        # 启动库
        self.lib.start()
        
        print(f"[PJSIP] SIP 库已启动")
    
    def register(self) -> bool:
        """注册到 SIP 服务器"""
        if not self.lib:
            self.start()
        
        # 创建账户配置
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{self.config['username']}@{self.config['server_ip']}"
        acc_cfg.regConfig.registrarUri = f"sip:{self.config['server_ip']}:{self.config['server_port']}"
        
        # 设置认证
        cred = pj.AuthCredInfo()
        cred.realm = "*"
        cred.scheme = "digest"
        cred.username = self.config['username']
        cred.data = self.config['password']
        cred.dataType = pj.PJSIP_CRED_DATA_PLAIN_PASSWD
        
        acc_cfg.sipConfig.authCreds.append(cred)
        
        # 创建账户
        self.acc = SIPAccount(self)
        self.acc.create(acc_cfg)
        
        # 等待注册完成
        max_wait = 10  # 最多等待 10 秒
        for _ in range(max_wait * 10):
            if self.registered:
                return True
            time.sleep(0.1)
        
        return False
    
    def dial(self, callee: str) -> bool:
        """发起呼叫"""
        if not self.registered:
            print(f"[ERROR] 未注册，无法发起呼叫")
            return False
        
        # 创建呼叫
        call = SIPCall(self.acc, client=self)
        call_param = pj.CallOpParam()
        call_param.opt.audioCount = 1
        call_param.opt.videoCount = 0
        
        call.makeCall(f"sip:{callee}@{self.config['server_ip']}", call_param)
        
        self.current_call = call
        
        # 等待呼叫建立
        max_wait = 30  # 最多等待 30 秒
        for _ in range(max_wait * 10):
            if call.getInfo().state == pj.PJSIP_INV_STATE_CONFIRMED:
                return True
            time.sleep(0.1)
        
        return False
    
    def play_media(self):
        """播放媒体文件"""
        media_file = self.config.get('media_file')
        if media_file and os.path.exists(media_file):
            print(f"[MEDIA] 开始播放: {media_file}")
            # 使用 PJSIP 的媒体播放功能
            # 这里需要实现音频文件播放
            pass
    
    def hangup(self):
        """挂断呼叫"""
        if self.current_call:
            call_param = pj.CallOpParam()
            self.current_call.hangup(call_param)
            self.current_call = None
    
    def stop(self):
        """停止 SIP 库"""
        if self.acc:
            self.acc.delete()
        if self.lib:
            self.lib.destroy()


def main():
    """主函数"""
    import sys
    import os
    
    print("=" * 60)
    print("SIP 客户端 (使用 PJSIP)")
    print("=" * 60)
    print()
    
    # 加载配置
    config_file = "sip_client_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG.copy()
    
    # 创建客户端
    client = PJSIPClient(config)
    
    try:
        # 注册
        print("[1/2] 正在注册...")
        if not client.register():
            print("[ERROR] 注册失败")
            sys.exit(1)
        
        print()
        print("[2/2] 注册成功！")
        print()
        
        # 交互式菜单
        while True:
            print("\n" + "=" * 60)
            print("SIP 客户端 - 命令菜单")
            print("=" * 60)
            print("1. 发起呼叫")
            print("2. 挂断呼叫")
            print("3. 退出")
            print()
            
            choice = input("请选择操作 (1-3): ").strip()
            
            if choice == "1":
                callee = input("请输入被叫号码: ").strip()
                if callee:
                    print(f"\n正在呼叫 {callee}...")
                    client.dial(callee)
            
            elif choice == "2":
                if client.current_call:
                    client.hangup()
                else:
                    print("[INFO] 当前没有活跃的呼叫")
            
            elif choice == "3":
                break
            
            else:
                print("[ERROR] 无效选择")
    
    finally:
        # 清理
        client.stop()


if __name__ == "__main__":
    import os
    main()

