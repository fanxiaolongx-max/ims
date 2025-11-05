#!/bin/bash
# SIP 服务器快速测试脚本

echo "========================================="
echo "  SIP 服务器快速测试"
echo "========================================="
echo ""

# 检查服务器是否运行
echo "1. 检查 SIP 服务器状态..."
if ! pgrep -f "python.*run.py" > /dev/null; then
    echo "   ⚠️  服务器未运行！请先启动："
    echo "      python run.py"
    echo ""
    exit 1
else
    echo "   ✓ 服务器正在运行"
fi

echo ""
echo "2. 检查测试用户..."
if ! grep -q '"1001"' data/users.json; then
    echo "   ⚠️  测试用户不存在！请添加用户："
    echo "      访问 http://localhost:8888"
    echo "      执行: ADD USER USERNAME=1001 PASSWORD=1001 STATUS=ACTIVE"
    echo "      执行: ADD USER USERNAME=1002 PASSWORD=1002 STATUS=ACTIVE"
    echo "      执行: ADD USER USERNAME=1003 PASSWORD=1003 STATUS=ACTIVE"
    echo ""
    exit 1
else
    echo "   ✓ 测试用户已存在"
fi

echo ""
echo "3. 选择测试场景："
echo "   1 - 正常呼叫（推荐）"
echo "   2 - 被叫忙"
echo "   3 - 振铃时取消"
echo "   4 - 被叫未注册"
echo "   5 - 即时消息（推荐）"
echo "   6 - 注册注销（推荐）"
echo "   7 - 错误密码"
echo "   8 - 并发呼叫"
echo "   9 - 长时间通话"
echo "   10 - 重复注册"
echo "   all - 运行所有测试"
echo ""
read -p "请输入场景编号 [6]: " scenario

# 默认场景 6
scenario=${scenario:-6}

echo ""
echo "4. 运行测试..."
echo ""

if [ "$scenario" == "all" ]; then
    python3 test_sip_scenarios.py
else
    python3 test_sip_scenarios.py "$scenario"
fi

echo ""
echo "========================================="
echo "  测试完成！"
echo "========================================="
echo ""
echo "查看测试结果："
echo "  • MML 界面: http://localhost:8888"
echo "  • CDR 记录: cat CDR/\$(date +%Y-%m-%d)/cdr_*.csv"
echo "  • 服务器日志: tail -f logs/\$(date +%Y-%m-%d)/ims-sip-server.log"
echo ""

