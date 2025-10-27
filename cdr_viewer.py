#!/usr/bin/env python3
"""
CDR 查看和统计工具
用于查看、分析和统计 CDR 话单数据
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def print_separator(title="", width=100):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 10} {title} {'=' * (width - len(title) - 12)}")
    else:
        print("=" * width)


def load_cdr_file(date_str=None):
    """
    加载 CDR 文件
    
    Args:
        date_str: 日期字符串 (YYYY-MM-DD)，默认今天
        
    Returns:
        (records, file_path) 元组
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    cdr_dir = Path("CDR") / date_str
    cdr_file = cdr_dir / f"cdr_{date_str}.csv"
    
    if not cdr_file.exists():
        return None, cdr_file
    
    records = []
    with open(cdr_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    
    return records, cdr_file


def show_statistics(date_str=None):
    """显示 CDR 统计信息"""
    records, cdr_file = load_cdr_file(date_str)
    
    if records is None:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return
    
    print_separator(f"CDR 统计报告 - {date_str or '今天'}")
    print(f"📁 文件: {cdr_file}")
    print(f"📊 总记录数: {len(records)}\n")
    
    # 按记录类型统计
    type_counts = defaultdict(int)
    for r in records:
        type_counts[r['record_type']] += 1
    
    print("📈 记录类型分布:")
    print("-" * 60)
    for rtype in sorted(type_counts.keys()):
        count = type_counts[rtype]
        percentage = (count / len(records) * 100) if records else 0
        bar = "█" * int(percentage / 2)
        print(f"  {rtype:25s} | {count:5d} ({percentage:5.1f}%) {bar}")
    
    # 统计注册信息
    register_success = sum(1 for r in records if r['record_type'] == 'REGISTER_SUCCESS')
    register_fail = sum(1 for r in records if r['record_type'] == 'REGISTER_FAIL')
    unregister = sum(1 for r in records if r['record_type'] == 'UNREGISTER')
    
    if register_success or register_fail or unregister:
        print(f"\n📝 注册统计:")
        print("-" * 60)
        print(f"  成功注册: {register_success}")
        print(f"  失败注册: {register_fail}")
        print(f"  注销: {unregister}")
    
    # 统计呼叫信息
    call_start = sum(1 for r in records if r['record_type'] == 'CALL_START')
    call_answer = sum(1 for r in records if r['record_type'] == 'CALL_ANSWER')
    call_end = sum(1 for r in records if r['record_type'] == 'CALL_END')
    call_fail = sum(1 for r in records if r['record_type'] == 'CALL_FAIL')
    call_cancel = sum(1 for r in records if r['record_type'] == 'CALL_CANCEL')
    
    if call_start or call_answer or call_end or call_fail or call_cancel:
        print(f"\n📞 呼叫统计:")
        print("-" * 60)
        print(f"  呼叫开始: {call_start}")
        print(f"  呼叫应答: {call_answer}")
        print(f"  呼叫结束: {call_end}")
        print(f"  呼叫失败: {call_fail}")
        print(f"  呼叫取消: {call_cancel}")
        
        if call_answer and call_start:
            success_rate = (call_answer / call_start * 100)
            print(f"  接通率: {success_rate:.1f}%")
        
        # 计算平均通话时长
        durations = [float(r['duration']) for r in records 
                    if r['record_type'] == 'CALL_END' and r['duration']]
        if durations:
            avg_duration = sum(durations) / len(durations)
            total_duration = sum(durations)
            print(f"  平均通话时长: {avg_duration:.1f} 秒")
            print(f"  总通话时长: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)")
    
    # 统计短信
    messages = sum(1 for r in records if r['record_type'] == 'MESSAGE')
    if messages:
        print(f"\n💬 短信统计:")
        print("-" * 60)
        print(f"  短信数量: {messages}")
    
    # 统计用户活跃度
    user_activity = defaultdict(int)
    for r in records:
        caller = r.get('caller_number', '')
        if caller:
            user_activity[caller] += 1
    
    if user_activity:
        print(f"\n👥 用户活跃度 TOP 10:")
        print("-" * 60)
        sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (user, count) in enumerate(sorted_users, 1):
            print(f"  {i:2d}. {user:15s} | {count:5d} 条记录")
    
    print_separator()


def show_recent_records(date_str=None, limit=20, record_type=None):
    """显示最近的 CDR 记录"""
    records, cdr_file = load_cdr_file(date_str)
    
    if records is None:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return
    
    if record_type:
        records = [r for r in records if r['record_type'] == record_type]
        title = f"最近 {limit} 条 {record_type} 记录"
    else:
        title = f"最近 {limit} 条记录"
    
    print_separator(title)
    print(f"📁 文件: {cdr_file}\n")
    
    if not records:
        print("❌ 没有找到记录")
        return
    
    # 显示最近的记录
    recent = records[-limit:] if len(records) > limit else records
    recent.reverse()  # 最新的在前
    
    for i, r in enumerate(recent, 1):
        # 兼容新旧格式
        time_str = r.get('start_time') or r.get('time', '')
        record_type = r.get('record_type', '')
        call_state = r.get('call_state', '')
        
        # 显示记录类型和状态
        if call_state:
            print(f"{i}. [{time_str}] {record_type} ({call_state})")
        else:
            print(f"{i}. [{time_str}] {record_type}")
        
        # 显示 Call-ID（截取前20个字符）
        call_id = r.get('call_id', '')
        if call_id and len(call_id) > 30:
            print(f"   Call-ID: {call_id[:30]}...")
        else:
            print(f"   Call-ID: {call_id}")
        
        # 显示主被叫信息
        caller_uri = r.get('caller_uri', '')
        caller_number = r.get('caller_number', '')
        if caller_number:
            caller_info = f"{caller_number}"
            if r.get('caller_ip'):
                caller_info += f" ({r['caller_ip']}:{r['caller_port']})"
            print(f"   主叫: {caller_info}")
        elif caller_uri:
            print(f"   主叫: {caller_uri}")
        
        callee_number = r.get('callee_number', '')
        callee_uri = r.get('callee_uri', '')
        if callee_number:
            callee_info = f"{callee_number}"
            if r.get('callee_ip'):
                callee_info += f" ({r['callee_ip']}:{r['callee_port']})"
            print(f"   被叫: {callee_info}")
        elif callee_uri:
            print(f"   被叫: {callee_uri}")
        
        # 显示呼叫时间信息
        if r.get('duration'):
            print(f"   通话时长: {r['duration']} 秒")
        if r.get('setup_time'):
            print(f"   建立时间: {r['setup_time']} 毫秒")
        
        # 显示各阶段时间（合并模式）
        if r.get('invite_time'):
            print(f"   INVITE: {r['invite_time']}")
        if r.get('answer_time'):
            print(f"   ANSWER: {r['answer_time']}")
        if r.get('bye_time'):
            print(f"   BYE: {r['bye_time']}")
        
        # 显示状态
        if r.get('status_code'):
            print(f"   状态: {r['status_code']} {r.get('status_text', '')}")
        if r.get('termination_reason'):
            print(f"   终止原因: {r['termination_reason']}")
        
        # 显示消息内容
        if r.get('message_body'):
            msg = r['message_body'][:100]
            print(f"   内容: {msg}{'...' if len(r['message_body']) > 100 else ''}")
        
        # 显示注册信息
        if r.get('expires'):
            print(f"   过期时间: {r['expires']} 秒")
        
        print()
    
    print_separator()


def show_call_details(call_id, date_str=None):
    """显示特定呼叫的详细信息"""
    records, cdr_file = load_cdr_file(date_str)
    
    if records is None:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return
    
    # 查找该 Call-ID 的所有记录
    call_records = [r for r in records if r['call_id'] == call_id]
    
    if not call_records:
        print(f"❌ 没有找到 Call-ID: {call_id}")
        return
    
    print_separator(f"呼叫详情 - {call_id}")
    
    for i, r in enumerate(call_records, 1):
        record_type = r.get('record_type', '')
        call_state = r.get('call_state', '')
        
        if call_state:
            print(f"\n记录 {i}: {record_type} ({call_state})")
        else:
            print(f"\n记录 {i}: {record_type}")
        print("-" * 60)
        
        # 时间信息（兼容新旧格式）
        date = r.get('date', '')
        start_time = r.get('start_time') or r.get('time', '')
        end_time = r.get('end_time', '')
        
        print(f"  日期: {date}")
        print(f"  开始时间: {start_time}")
        if end_time:
            print(f"  结束时间: {end_time}")
        
        # 主被叫信息
        if r.get('caller_uri'):
            caller_info = r['caller_uri']
            if r.get('caller_number'):
                caller_info += f" ({r['caller_number']})"
            print(f"  主叫: {caller_info}")
        if r.get('caller_ip'):
            print(f"  主叫地址: {r['caller_ip']}:{r.get('caller_port', '')}")
        
        if r.get('callee_uri'):
            callee_info = r['callee_uri']
            if r.get('callee_number'):
                callee_info += f" ({r['callee_number']})"
            print(f"  被叫: {callee_info}")
        if r.get('callee_ip'):
            print(f"  被叫地址: {r['callee_ip']}:{r.get('callee_port', '')}")
        
        # 呼叫详情
        if r.get('duration'):
            print(f"  通话时长: {r['duration']} 秒")
        if r.get('setup_time'):
            print(f"  建立时间: {r['setup_time']} 毫秒")
        
        # 各阶段时间（合并模式）
        if r.get('invite_time'):
            print(f"  INVITE 时间: {r['invite_time']}")
        if r.get('ringing_time'):
            print(f"  振铃时间: {r['ringing_time']}")
        if r.get('answer_time'):
            print(f"  应答时间: {r['answer_time']}")
        if r.get('bye_time'):
            print(f"  结束时间: {r['bye_time']}")
        
        # 状态信息
        if r.get('status_code'):
            print(f"  状态码: {r['status_code']} {r.get('status_text', '')}")
        if r.get('termination_reason'):
            print(f"  终止原因: {r['termination_reason']}")
        
        # 其他信息
        if r.get('user_agent'):
            print(f"  User-Agent: {r['user_agent']}")
        if r.get('contact'):
            print(f"  Contact: {r['contact']}")
        if r.get('expires'):
            print(f"  Expires: {r['expires']}")
        if r.get('cseq'):
            print(f"  CSeq: {r['cseq']}")
    
    print_separator()


def export_to_csv(date_str=None, output_file=None, record_type=None):
    """导出 CDR 到新的 CSV 文件（可按类型过滤）"""
    records, cdr_file = load_cdr_file(date_str)
    
    if records is None:
        print(f"❌ CDR 文件不存在: {cdr_file}")
        return
    
    if record_type:
        records = [r for r in records if r['record_type'] == record_type]
    
    if not records:
        print(f"❌ 没有找到记录")
        return
    
    if output_file is None:
        output_file = f"cdr_export_{date_str or 'today'}_{record_type or 'all'}.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    
    print(f"✅ 已导出 {len(records)} 条记录到: {output_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CDR 话单查看和统计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s stats                          # 显示今天的统计
  %(prog)s stats --date 2025-10-27        # 显示指定日期的统计
  %(prog)s recent                         # 显示最近 20 条记录
  %(prog)s recent --limit 50              # 显示最近 50 条记录
  %(prog)s recent --type CALL_START       # 只显示呼叫开始记录
  %(prog)s call <Call-ID>                 # 显示特定呼叫的详情
  %(prog)s export --type REGISTER_SUCCESS # 导出成功注册记录
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    
    # recent 命令
    recent_parser = subparsers.add_parser('recent', help='显示最近的记录')
    recent_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    recent_parser.add_argument('--limit', '-n', type=int, default=20, help='显示条数')
    recent_parser.add_argument('--type', '-t', help='记录类型过滤')
    
    # call 命令
    call_parser = subparsers.add_parser('call', help='显示呼叫详情')
    call_parser.add_argument('call_id', help='Call-ID')
    call_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出 CDR')
    export_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    export_parser.add_argument('--type', '-t', help='记录类型过滤')
    export_parser.add_argument('--output', '-o', help='输出文件名')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'stats':
        show_statistics(args.date)
    elif args.command == 'recent':
        show_recent_records(args.date, args.limit, args.type)
    elif args.command == 'call':
        show_call_details(args.call_id, args.date)
    elif args.command == 'export':
        export_to_csv(args.date, args.output, args.type)


if __name__ == '__main__':
    main()

