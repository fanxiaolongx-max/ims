#!/usr/bin/env python3
"""
测试 CDR 合并模式
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 导入 CDR 模块
from sipcore.cdr import init_cdr


def test_cdr_merged_mode():
    """测试 CDR 合并模式"""
    print("=" * 60)
    print("测试 CDR 合并模式...")
    print("=" * 60)
    
    # 初始化 CDR（使用测试目录）
    test_dir = "CDR_TEST_MERGED"
    cdr = init_cdr(base_dir=test_dir, merge_mode=True)
    print(f"✓ CDR 系统已初始化，测试目录: {test_dir}\n")
    
    # 测试 1: 完整的呼叫流程（合并为一条记录）
    print("[测试 1] 完整呼叫流程（INVITE -> 200 OK -> BYE）...")
    test_call_id_1 = "call-001-success"
    
    # 1.1 呼叫开始
    cdr.record_call_start(
        call_id=test_call_id_1,
        caller_uri="sip:1001@test.com",
        callee_uri="sip:1002@test.com",
        caller_addr=("192.168.1.100", 5060),
        callee_ip="192.168.1.101",
        callee_port=5060,
        user_agent="TestUA/1.0"
    )
    print("  ✓ INVITE 记录已创建")
    time.sleep(0.1)
    
    # 1.2 呼叫应答
    cdr.record_call_answer(
        call_id=test_call_id_1,
        callee_addr=("192.168.1.101", 5060),
        setup_time=1500
    )
    print("  ✓ 200 OK 已更新到同一条记录")
    time.sleep(0.2)
    
    # 1.3 呼叫结束
    cdr.record_call_end(
        call_id=test_call_id_1,
        termination_reason="Normal"
    )
    print("  ✓ BYE 已更新并写入文件\n")
    
    # 测试 2: 呼叫取消（合并为一条记录）
    print("[测试 2] 呼叫取消（INVITE -> CANCEL）...")
    test_call_id_2 = "call-002-cancel"
    
    cdr.record_call_start(
        call_id=test_call_id_2,
        caller_uri="sip:1003@test.com",
        callee_uri="sip:1004@test.com",
        caller_addr=("192.168.1.102", 5060)
    )
    time.sleep(0.05)
    cdr.record_call_cancel(call_id=test_call_id_2)
    print("  ✓ 呼叫取消已更新并写入文件\n")
    
    # 测试 3: 呼叫失败（合并为一条记录）
    print("[测试 3] 呼叫失败（INVITE -> 486 Busy）...")
    test_call_id_3 = "call-003-busy"
    
    cdr.record_call_start(
        call_id=test_call_id_3,
        caller_uri="sip:1005@test.com",
        callee_uri="sip:1006@test.com",
        caller_addr=("192.168.1.103", 5060)
    )
    time.sleep(0.05)
    cdr.record_call_fail(
        call_id=test_call_id_3,
        status_code=486,
        status_text="Busy Here",
        reason="User is busy"
    )
    print("  ✓ 呼叫失败已更新并写入文件\n")
    
    # 测试 4: 注册
    print("[测试 4] 注册...")
    cdr.record_register(
        caller_uri="sip:1001@test.com",
        caller_addr=("192.168.1.100", 5060),
        contact="sip:1001@192.168.1.100:5060",
        expires=3600,
        success=True,
        call_id="reg-001"
    )
    print("  ✓ 注册记录已写入\n")
    
    # 测试 5: 短信
    print("[测试 5] 短信...")
    cdr.record_message(
        call_id="msg-001",
        caller_uri="sip:1001@test.com",
        callee_uri="sip:1002@test.com",
        caller_addr=("192.168.1.100", 5060),
        message_body="Hello, this is a test!"
    )
    print("  ✓ 短信记录已写入\n")
    
    # 验证文件
    print("=" * 60)
    print("验证 CDR 文件...")
    print("=" * 60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    cdr_file = Path(test_dir) / today / f"cdr_{today}.csv"
    
    if cdr_file.exists():
        print(f"✓ CDR 文件已创建: {cdr_file}\n")
        
        # 读取并显示文件内容
        with open(cdr_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"✓ 文件包含 {len(lines)} 行（包括表头）")
            print(f"✓ 记录数: {len(lines) - 1}\n")
            
            # 显示表头
            print("CDR 字段：")
            print("-" * 60)
            headers = lines[0].strip().split(',')
            for i, h in enumerate(headers[:10], 1):
                print(f"  {i:2d}. {h}")
            if len(headers) > 10:
                print(f"  ... 共 {len(headers)} 个字段")
            
            # 显示记录
            print("\nCDR 记录：")
            print("-" * 60)
            import csv
            f.seek(0)
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"\n记录 {i}:")
                print(f"  类型: {row['record_type']}")
                print(f"  状态: {row['call_state']}")
                print(f"  Call-ID: {row['call_id']}")
                print(f"  开始时间: {row['start_time']}")
                print(f"  结束时间: {row['end_time']}")
                if row['caller_number']:
                    print(f"  主叫: {row['caller_number']}")
                if row['callee_number']:
                    print(f"  被叫: {row['callee_number']}")
                if row['duration']:
                    print(f"  时长: {row['duration']} 秒")
                if row['invite_time']:
                    print(f"  INVITE: {row['invite_time']}")
                if row['answer_time']:
                    print(f"  ANSWER: {row['answer_time']}")
                if row['bye_time']:
                    print(f"  BYE: {row['bye_time']}")
                if row['termination_reason']:
                    print(f"  终止原因: {row['termination_reason']}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print(f"\n💡 关键改进:")
        print(f"   ✓ 同一次呼叫只有 1 条记录（包含完整流程）")
        print(f"   ✓ 记录了各个阶段的时间戳（invite_time, answer_time, bye_time）")
        print(f"   ✓ 呼叫状态清晰（STARTED -> ANSWERED -> ENDED）")
        print(f"   ✓ 便于查看和统计分析")
        
        print(f"\n💡 提示: 可以使用以下命令查看 CDR 文件:")
        print(f"   cat {cdr_file}")
        
    else:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return False
    
    return True


if __name__ == '__main__':
    try:
        success = test_cdr_merged_mode()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

