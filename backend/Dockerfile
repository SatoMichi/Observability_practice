# Python 3.11スリム版（軽量）
FROM python:3.11-slim as base

WORKDIR /app

# システム依存関係の最適化インストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python依存関係（キャッシュ最適化）
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check --no-warn-script-location \
    -r requirements.txt

# NLTKデータのダウンロード（キャッシュレイヤー分離）
RUN python -c "import nltk; nltk.download('gutenberg', quiet=True); nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# アプリケーションコード（最後にコピーでキャッシュ効率向上）
COPY . .

# 非特権ユーザーでの実行（セキュリティ向上）
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "main.py"] 
