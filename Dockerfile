FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 基础依赖（时区等），如需额外系统库可在此添加
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# 若存在 requirements.txt 则安装，否则跳过
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple ; \
    else \
      echo "no requirements.txt, skip pip install"; \
    fi

# MML Web 端口（host 网络下可不 EXPOSE，声明不影响）
EXPOSE 8888/tcp 8889/tcp

# 环境变量说明（可选，实际运行时通过 docker run -e 传递）：
# SERVER_IP - 服务器IP地址（默认自动检测）
# LOCAL_NETWORK_CIDR - 局域网网段（默认 192.168.0.0/16）

# 运行主程序
CMD ["python", "run.py"]