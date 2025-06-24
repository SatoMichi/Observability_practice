import json
import string
import time
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# NLTKの初期設定
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/gutenberg')
except LookupError:
    nltk.download('gutenberg')

from nltk.corpus import gutenberg, stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# JSON構造化ログシステムをインポート
from log_system import setup_logger

# ロガーの設定
logger = setup_logger("search_app")

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
    
    try:
        start_time = time.time()
        logger.info("アプリケーション起動開始", extra={"event_type": "startup"})
        
        # Gutenbergコーパスから書籍を取得
        fileids = gutenberg.fileids()
        
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
                
            except Exception as e:
                logger.error("書籍処理エラー", extra={"event_type": "book_processing_error", "book_id": fileid, "error": str(e)})
        
        # TF-IDFベクトル化
        texts_list = list(processed_texts.values())
        tfidf_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        tfidf_matrix = tfidf_vectorizer.fit_transform(texts_list)
        
        total_time = time.time() - start_time
        logger.info("アプリケーション起動完了", extra={"event_type": "startup_complete", "duration_seconds": round(total_time, 2), "books_count": len(books_data)})
    except Exception as e:
        logger.error("起動エラー", extra={"event_type": "startup_error", "error": str(e)})

@app.get("/")
async def root():
    return {"message": "全文検索API"}

@app.get("/books")
async def get_books():
    """全書籍の情報を返す"""
    start_time = time.time()
    
    books_list = []
    for book_id, book_info in books_data.items():
        books_list.append({
            'id': book_id,
            'title': book_info['title'],
            'author': book_info['author'],
            'word_count': book_info['word_count']
        })
    
    response_time = time.time() - start_time
    logger.info("書籍一覧API", extra={"event_type": "api_response", "endpoint": "/books", "response_count": len(books_list), "duration_ms": round(response_time * 1000, 3)})
    
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
    
    if not q or not q.strip():
        logger.warning("空の検索クエリ", extra={"event_type": "search_validation_error", "query": q})
        raise HTTPException(status_code=400, detail="検索クエリが空です")
    
    try:
        # 検索実行
        results = perform_search(q, search_method="tfidf")
        
        response_time = time.time() - start_time
        logger.info("検索API", extra={"event_type": "search_complete", "query": q, "results_count": len(results), "duration_ms": round(response_time * 1000, 3)})
        
        return {
            'query': q,
            'total_results': len(results),
            'results': results
        }
    except Exception as e:
        error_time = time.time() - start_time
        logger.error("検索エラー", extra={"event_type": "search_error", "query": q, "error": str(e), "duration_ms": round(error_time * 1000, 3)})
        raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
