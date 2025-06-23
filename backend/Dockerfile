# ========== Builder Stage ==========
FROM python:3.11-slim as builder

WORKDIR /app

# システム依存関係（ビルド用）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        && \
    rm -rf /var/lib/apt/lists/*

# Python依存関係のビルド
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ========== Runtime Stage ==========
FROM python:3.11-slim as runtime

WORKDIR /app

# ランタイム用の最小システム依存関係
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ビルド済みwheelをコピーしてインストール
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt && \
    rm -rf /wheels

# NLTKデータのダウンロード
RUN python -c "import nltk; nltk.download('gutenberg', quiet=True); nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# アプリケーションコード
COPY . .

# 非特権ユーザー
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "main.py"] 
