# 三羊系统统一运行环境（Python 3.11，与生产容器一致）
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 条码/二维码等依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 仅复制 Python 与脚本；JSON/HTML 由宿主机卷挂载（部署不覆盖 admin 配置）
COPY *.py ./
COPY scripts/ ./scripts/

# 默认启动客服端；生产端在 compose 中覆盖 command
EXPOSE 3001 3002

CMD ["python", "app_cs.py"]
