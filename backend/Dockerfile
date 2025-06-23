FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# NLTKデータ
RUN python -c "import nltk; nltk.download('gutenberg'); nltk.download('punkt'); nltk.download('stopwords')"

EXPOSE 8000
CMD ["python", "main.py"] 
