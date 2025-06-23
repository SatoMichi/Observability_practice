# Python 3.11スリム版で高速ビルド
FROM python:3.11-slim

WORKDIR /app

# 最小システム依存関係（ビルド + ランタイム一括）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

# Python依存関係（高速インストール）
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check \
    -r requirements.txt && \
    apt-get purge -y gcc && \
    apt-get autoremove -y

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
