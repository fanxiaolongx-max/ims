#!/usr/bin/env python3
"""
CDR 系统测试脚本
验证 CDR 功能是否正常工作
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 导入 CDR 模块
from sipcore.cdr import init_cdr, CDRType


def test_cdr_basic():
    """测试基本的 CDR 功能"""
    print("=" * 60)
    print("开始测试 CDR 系统...")
    print("=" * 60)
    
    # 初始化 CDR（使用测试目录）
    test_dir = "CDR_TEST"
    cdr = init_cdr(base_dir=test_dir)
    print(f"✓ CDR 系统已初始化，测试目录: {test_dir}")
    
    # 测试 1: 注册成功
    print("\n[测试 1] 注册成功...")
    cdr.record_register(
        caller_uri="sip:1001@test.com",
        caller_addr=("192.168.1.100", 5060),
        contact="sip:1001@192.168.1.100:5060",
        expires=3600,
        success=True,
        status_code=200,
        status_text="OK",
        call_id="test-call-id-001",
        user_agent="TestUA/1.0",
        cseq="1 REGISTER"
    )
    print("✓ 注册成功记录已写入")
    
    # 测试 2: 呼叫流程
    print("\n[测试 2] 呼叫流程...")
    test_call_id = "test-call-id-002"
    
    # 2.1 呼叫开始
    cdr.record_call_start(
        call_id=test_call_id,
        caller_uri="sip:1001@test.com",
        callee_uri="sip:1002@test.com",
        caller_addr=("192.168.1.100", 5060),
        callee_ip="192.168.1.101",
        callee_port=5060,
        user_agent="TestUA/1.0"
    )
    print("  ✓ 呼叫开始记录已写入")
    
    # 2.2 呼叫应答
    cdr.record_call_answer(
        call_id=test_call_id,
        callee_addr=("192.168.1.101", 5060),
        setup_time=1500
    )
    print("  ✓ 呼叫应答记录已写入")
    
    # 模拟通话中...
    import time
    time.sleep(0.1)
    
    # 2.3 呼叫结束
    cdr.record_call_end(
        call_id=test_call_id,
        termination_reason="Normal"
    )
    print("  ✓ 呼叫结束记录已写入")
    
    # 测试 3: 呼叫取消
    print("\n[测试 3] 呼叫取消...")
    test_call_id_cancel = "test-call-id-003"
    cdr.record_call_start(
        call_id=test_call_id_cancel,
        caller_uri="sip:1003@test.com",
        callee_uri="sip:1004@test.com",
        caller_addr=("192.168.1.102", 5060)
    )
    cdr.record_call_cancel(call_id=test_call_id_cancel)
    print("✓ 呼叫取消记录已写入")
    
    # 测试 4: 呼叫失败
    print("\n[测试 4] 呼叫失败...")
    test_call_id_fail = "test-call-id-004"
    cdr.record_call_start(
        call_id=test_call_id_fail,
        caller_uri="sip:1005@test.com",
        callee_uri="sip:1006@test.com",
        caller_addr=("192.168.1.103", 5060)
    )
    cdr.record_call_fail(
        call_id=test_call_id_fail,
        status_code=486,
        status_text="Busy Here",
        reason="User is busy"
    )
    print("✓ 呼叫失败记录已写入")
    
    # 测试 5: 短信
    print("\n[测试 5] 短信...")
    cdr.record_message(
        call_id="test-call-id-005",
        caller_uri="sip:1001@test.com",
        callee_uri="sip:1002@test.com",
        caller_addr=("192.168.1.100", 5060),
        message_body="Hello, this is a test message!"
    )
    print("✓ 短信记录已写入")
    
    # 测试 6: OPTIONS
    print("\n[测试 6] OPTIONS...")
    cdr.record_options(
        caller_uri="sip:1001@test.com",
        callee_uri="sip:test.com",
        caller_addr=("192.168.1.100", 5060),
        call_id="test-call-id-006"
    )
    print("✓ OPTIONS 记录已写入")
    
    # 测试 7: 注销
    print("\n[测试 7] 注销...")
    cdr.record_unregister(
        caller_uri="sip:1001@test.com",
        caller_addr=("192.168.1.100", 5060),
        contact="sip:1001@192.168.1.100:5060",
        call_id="test-call-id-007"
    )
    print("✓ 注销记录已写入")
    
    # 验证文件
    print("\n" + "=" * 60)
    print("验证 CDR 文件...")
    print("=" * 60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    cdr_file = Path(test_dir) / today / f"cdr_{today}.csv"
    
    if cdr_file.exists():
        print(f"✓ CDR 文件已创建: {cdr_file}")
        
        # 读取并显示文件内容
        with open(cdr_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"✓ 文件包含 {len(lines)} 行（包括表头）")
            print(f"✓ 记录数: {len(lines) - 1}")
            
            # 显示前几行
            print("\n文件内容预览（前 3 条记录）:")
            print("-" * 60)
            for i, line in enumerate(lines[:4]):  # 表头 + 前3条
                if i == 0:
                    print(f"表头: {line.strip()[:100]}...")
                else:
                    print(f"记录{i}: {line.strip()[:100]}...")
        
        # 获取统计信息
        stats = cdr.get_stats(today)
        print("\n统计信息:")
        print("-" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print(f"\n💡 提示: 可以使用以下命令查看 CDR 文件:")
        print(f"   cat {cdr_file}")
        print(f"   python3 cdr_viewer.py stats")
        print(f"   python3 cdr_viewer.py recent")
        
    else:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return False
    
    return True


if __name__ == '__main__':
    try:
        success = test_cdr_basic()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

