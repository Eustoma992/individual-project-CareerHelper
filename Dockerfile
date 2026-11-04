FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# 中文字体（词云/matplotlib）+ ctranslate2 运行所需的 OpenMP + 健康检查工具
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
        libgomp1 \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 作答记录写在容器内 /app/data；如需持久化，挂载卷并设置 JOBPREP_DATA_DIR
ENV JOBPREP_DATA_DIR=/app/data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", "--server.address=0.0.0.0"]
