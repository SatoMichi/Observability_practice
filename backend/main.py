import nltk
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import string
from typing import List, Dict, Any
import uvicorn
import logging
import time
import json
from datetime import datetime, timezone

# NLTK データのダウンロード
try:
    nltk.data.find('corpora/gutenberg')
except LookupError:
    nltk.download('gutenberg')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

from nltk.corpus import gutenberg, stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import structlog

# JSON構造化ログの設定
def json_formatter(logger, name, event_dict):
    """JSON形式でログを出力するフォーマッター"""
    # タイムスタンプをISO 8601形式で追加
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 基本構造
    log_record = {
        "timestamp": timestamp,
        "level": event_dict.get("level", "INFO").upper(),
        "event": event_dict.get("event", "unknown"),
        "message": event_dict.get("message", "")
    }
    
    # 追加フィールドをマージ
    for key, value in event_dict.items():
        if key not in ["level", "event", "message"]:
            log_record[key] = value
    
    return json.dumps(log_record, ensure_ascii=False)

# structlogの設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        json_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("search_app")

app = FastAPI(title="全文検索API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite と CRA のデフォルトポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数
books_data = {}
tfidf_vectorizer = None
tfidf_matrix = None
processed_texts = {}

def preprocess_text(text: str) -> str:
    """テキストの前処理"""
    # 小文字化
    text = text.lower()
    # 句読点の除去
    text = text.translate(str.maketrans('', '', string.punctuation))
    # トークン化
    tokens = word_tokenize(text)
    # ストップワード除去
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
    return ' '.join(tokens)

def get_snippet(text: str, query: str, context_length: int = 25) -> str:
    """検索クエリを含むスニペットを取得"""
    sentences = sent_tokenize(text)
    query_words = query.lower().split()
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(word in sentence_lower for word in query_words):
            words = sentence.split()
            if len(words) <= context_length * 2:
                return sentence
            
            # より詳細な検索を行い、クエリワードの位置を特定
            for i, word in enumerate(words):
                if any(qword in word.lower() for qword in query_words):
                    start = max(0, i - context_length)
                    end = min(len(words), i + context_length)
                    snippet = ' '.join(words[start:end])
                    return snippet
    
    # 見つからない場合は最初の文の一部を返す
    first_sentence = sentences[0] if sentences else text[:200]
    words = first_sentence.split()
    if len(words) > context_length:
        return ' '.join(words[:context_length]) + "..."
    return first_sentence

@app.on_event("startup")
async def startup_event():
    """アプリ起動時にデータの読み込みとTF-IDFベクトル化を実行"""
    global books_data, tfidf_vectorizer, tfidf_matrix, processed_texts
    
    start_time = time.time()
    logger.info("アプリケーション起動開始", event="startup", message="アプリケーション起動開始")
    logger.info("書籍データを読み込み中", event="data_loading", message="書籍データを読み込み中")
    
    # Gutenbergコーパスから書籍を取得
    fileids = gutenberg.fileids()
    logger.info("利用可能な書籍数を確認", event="books_discovery", message="利用可能な書籍数を確認", books_available=len(fileids))
    
    for i, fileid in enumerate(fileids):
        try:
            raw_text = gutenberg.raw(fileid)
            processed_text = preprocess_text(raw_text)
            
            # 著者とタイトルを推定（ファイル名から）
            if '-' in fileid:
                parts = fileid.replace('.txt', '').split('-')
                author = parts[0].replace('_', ' ').title()
                title = '-'.join(parts[1:]).replace('_', ' ').title() if len(parts) > 1 else fileid
            else:
                title = fileid.replace('.txt', '').replace('_', ' ').title()
                author = "Unknown"
            
            books_data[fileid] = {
                'id': fileid,
                'title': title,
                'author': author,
                'raw_text': raw_text,
                'word_count': len(raw_text.split())
            }
            processed_texts[fileid] = processed_text
            
            if (i + 1) % 5 == 0:  # 5冊ごとに進捗をログ出力
                logger.info("書籍読み込み進捗", event="loading_progress", message="書籍読み込み進捗", books_loaded=i+1, total_books=len(fileids))
            
        except Exception as e:
            logger.error("書籍処理エラー", event="book_processing_error", message="書籍処理エラー", book_id=fileid, error=str(e))
    
    load_time = time.time() - start_time
    logger.info("書籍読み込み完了", event="loading_complete", message="書籍読み込み完了", books_count=len(books_data), duration_seconds=round(load_time, 2))
    
    # TF-IDFベクトル化
    vectorize_start = time.time()
    logger.info("TF-IDFベクトル化を実行中", event="tfidf_start", message="TF-IDFベクトル化を実行中")
    texts_list = list(processed_texts.values())
    tfidf_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    tfidf_matrix = tfidf_vectorizer.fit_transform(texts_list)
    
    vectorize_time = time.time() - vectorize_start
    total_time = time.time() - start_time
    logger.info("TF-IDFベクトル化完了", event="tfidf_complete", message="TF-IDFベクトル化完了", duration_seconds=round(vectorize_time, 2))
    logger.info("アプリケーション起動完了", event="startup_complete", message="アプリケーション起動完了", total_duration_seconds=round(total_time, 2), books_count=len(books_data))

@app.get("/")
async def root():
    return {"message": "全文検索API"}

@app.get("/books")
async def get_books():
    """全書籍の情報を返す"""
    start_time = time.time()
    logger.info("書籍一覧のリクエストを受信", event="api_request", message="書籍一覧のリクエストを受信", endpoint="/books")
    
    books_list = []
    for book_id, book_info in books_data.items():
        books_list.append({
            'id': book_id,
            'title': book_info['title'],
            'author': book_info['author'],
            'word_count': book_info['word_count']
        })
    
    response_time = time.time() - start_time
    logger.info("書籍一覧レスポンス完了", event="api_response", message="書籍一覧レスポンス完了", endpoint="/books", response_count=len(books_list), duration_ms=round(response_time * 1000, 3))
    
    return {"books": books_list}

def tfidf_search(query: str, max_results: int = 20, similarity_threshold: float = 0.01) -> List[Dict[str, Any]]:
    """TF-IDFベースの検索を実行
    
    Args:
        query: 検索クエリ
        max_results: 最大結果件数
        similarity_threshold: 類似度の閾値
        
    Returns:
        検索結果のリスト
    """
    # クエリの前処理
    processed_query = preprocess_text(query)
    if not processed_query:
        return []
    
    # TF-IDFベクトル化
    query_vector = tfidf_vectorizer.transform([processed_query])
    
    # コサイン類似度計算
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # 結果の整理
    results = []
    book_ids = list(books_data.keys())
    
    for i, similarity in enumerate(similarities):
        if similarity > similarity_threshold:
            book_id = book_ids[i]
            book_info = books_data[book_id]
            snippet = get_snippet(book_info['raw_text'], query)
            
            results.append({
                'id': book_id,
                'title': book_info['title'],
                'author': book_info['author'],
                'score': float(similarity),
                'snippet': snippet
            })
    
    # スコア順にソートして上位結果を返す
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:max_results]

def perform_search(query: str, search_method: str = "tfidf", **kwargs) -> List[Dict[str, Any]]:
    """検索を実行する統合インターフェース
    
    Args:
        query: 検索クエリ
        search_method: 検索手法 ("tfidf", "bm25", "dense" など)
        **kwargs: 各検索手法固有のパラメータ
        
    Returns:
        検索結果のリスト
    """
    if search_method == "tfidf":
        return tfidf_search(query, **kwargs)
    # elif search_method == "bm25":
    #     return bm25_search(query, **kwargs)
    # elif search_method == "dense":
    #     return dense_search(query, **kwargs)
    else:
        raise ValueError(f"Unsupported search method: {search_method}")

@app.get("/search")
async def search_books(q: str):
    """検索クエリに基づいて書籍を検索"""
    start_time = time.time()
    logger.info("検索リクエスト受信", event="search_request", message="検索リクエスト受信", query=q, endpoint="/search")
    
    if not q or not q.strip():
        logger.warning("空の検索クエリが送信されました", event="search_validation_error", message="空の検索クエリが送信されました", query=q)
        raise HTTPException(status_code=400, detail="検索クエリが空です")
    
    try:
        # 検索実行
        search_start = time.time()
        results = perform_search(q, search_method="tfidf")
        search_time = time.time() - search_start
        
        response_time = time.time() - start_time
        logger.info("検索完了", event="search_complete", message="検索完了", query=q, results_count=len(results), search_duration_ms=round(search_time * 1000, 3), total_duration_ms=round(response_time * 1000, 3))
        
        # 上位結果の詳細をログ出力
        if results:
            top_result = results[0]
            logger.info("最高スコア結果", event="search_top_result", message="最高スコア結果", query=q, top_title=top_result['title'], top_author=top_result['author'], top_score=round(top_result['score'], 4))
        
        return {
            'query': q,
            'total_results': len(results),
            'results': results
        }
    except Exception as e:
        error_time = time.time() - start_time
        logger.error("検索エラー", event="search_error", message="検索エラー", query=q, error=str(e), duration_ms=round(error_time * 1000, 3))
        raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
