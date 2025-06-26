import json
import string
import time
from typing import List, Dict, Any
import os
import requests

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry import propagate
import logging

# Feature Flags - Unleash
from UnleashClient import UnleashClient

# BM25 Search Algorithm
from rank_bm25 import BM25Okapi

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

# OpenTelemetryの初期化
def setup_tracing():
    """OpenTelemetryトレーシングの設定"""
    
    # リソース情報を設定
    resource = Resource(attributes={
        "service.name": "gutenberg-search-api",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # トレーサープロバイダーを設定
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # コンソールエクスポーター（デバッグ用）
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter
    console_exporter = ConsoleSpanExporter()
    console_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(console_processor)
    
    # OTLP Collectorが利用可能な場合のみOTLPエクスポーターを追加
    try:
        # OTLPエクスポーターの設定を試行
        response = requests.get("http://localhost:4318/v1/traces", timeout=1)
        
        # 接続成功した場合のみOTLPエクスポーターを追加
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4318/v1/traces",
            headers={}
        )
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(otlp_processor)
        print("🔗 OTLP Exporter configured: http://localhost:4318")
        
    except Exception as e:
        print(f"⚠️ OTLP Collector not available, using console output only: {e}")
        print("🖥️ Console Exporter configured for tracing")
    
    return trace.get_tracer(__name__)

# トレーサーの初期化
tracer = setup_tracing()

# Unleashクライアントの初期化
def setup_unleash():
    """Unleashクライアントの初期化"""
    unleash_url = os.getenv("UNLEASH_URL", "http://localhost:4242/api")
    unleash_token = os.getenv("UNLEASH_API_TOKEN", "default:development.unleash-insecure-client-api-token")
    
    try:
        # Unleashクライアントの初期化（認証なしでテスト）
        client = UnleashClient(
            url=unleash_url,
            app_name="gutenberg-search-api"
        )
        
        # 5秒間、接続試行を待つ
        print(f"📡 Unleash client connecting to: {unleash_url}")
        client.initialize_client()
        
        # 接続確認のための少し待機
        import time
        time.sleep(2)
        
        print(f"🚀 Unleash client initialized successfully")
        return client
    except Exception as e:
        print(f"⚠️ Unleash client initialization failed: {e}")
        print("   Continuing without feature flags...")
        return None

# Unleashクライアントの初期化
unleash_client = setup_unleash()

# ロガーの設定
logger = setup_logger("search_app")

# FastAPIアプリケーションの作成
app = FastAPI(
    title="Gutenberg Explorer API",
    description="古典文学検索のためのTF-IDF検索API",
    version="1.0.0"
)

# FastAPIのインストルメンテーション
FastAPIInstrumentor.instrument_app(app)

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
bm25_model = None
tokenized_corpus = []

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
    global books_data, tfidf_vectorizer, tfidf_matrix, processed_texts, bm25_model, tokenized_corpus
    
    with tracer.start_as_current_span("app_startup") as span:
        try:
            start_time = time.time()
            logger.info("アプリケーション起動開始", extra={"event_type": "startup"})
            
            # Gutenbergコーパスから書籍を取得
            with tracer.start_as_current_span("load_gutenberg_corpus") as load_span:
                fileids = gutenberg.fileids()
                load_span.set_attribute("corpus.total_files", len(fileids))
                
                for i, fileid in enumerate(fileids):
                    try:
                        with tracer.start_as_current_span("process_book", attributes={"book.id": fileid}):
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
            with tracer.start_as_current_span("tfidf_vectorization") as tfidf_span:
                texts_list = list(processed_texts.values())
                tfidf_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
                tfidf_matrix = tfidf_vectorizer.fit_transform(texts_list)
                
                tfidf_span.set_attribute("tfidf.max_features", 5000)
                tfidf_span.set_attribute("tfidf.ngram_range", "1,2")
                tfidf_span.set_attribute("tfidf.texts_count", len(texts_list))
                tfidf_span.set_attribute("tfidf.matrix_shape", str(tfidf_matrix.shape))
            
            # BM25モデルの初期化
            with tracer.start_as_current_span("bm25_initialization") as bm25_span:
                tokenized_corpus = [text.split() for text in texts_list]
                bm25_model = BM25Okapi(tokenized_corpus)
                
                bm25_span.set_attribute("bm25.corpus_size", len(tokenized_corpus))
                bm25_span.set_attribute("bm25.avg_doc_length", sum(len(doc) for doc in tokenized_corpus) / len(tokenized_corpus))
            
            total_time = time.time() - start_time
            span.set_attribute("startup.duration_seconds", round(total_time, 2))
            span.set_attribute("startup.books_loaded", len(books_data))
            
            logger.info("アプリケーション起動完了", extra={"event_type": "startup_complete", "duration_seconds": round(total_time, 2), "books_count": len(books_data)})
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
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
    with tracer.start_as_current_span("tfidf_search") as span:
        span.set_attribute("search.query", query)
        span.set_attribute("search.max_results", max_results)
        span.set_attribute("search.similarity_threshold", similarity_threshold)
        
        # クエリの前処理
        with tracer.start_as_current_span("preprocess_query") as preprocess_span:
            processed_query = preprocess_text(query)
            preprocess_span.set_attribute("query.original", query)
            preprocess_span.set_attribute("query.processed", processed_query)
            
            if not processed_query:
                span.set_attribute("search.results_count", 0)
                return []
        
        # TF-IDFベクトル化
        with tracer.start_as_current_span("vectorize_query") as vector_span:
            query_vector = tfidf_vectorizer.transform([processed_query])
            vector_span.set_attribute("vector.shape", str(query_vector.shape))
        
        # コサイン類似度計算
        with tracer.start_as_current_span("compute_similarity") as similarity_span:
            similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
            similarity_span.set_attribute("similarity.matrix_size", len(similarities))
        
        # 結果の整理
        with tracer.start_as_current_span("process_results") as results_span:
            results = []
            book_ids = list(books_data.keys())
            
            for i, similarity in enumerate(similarities):
                if similarity > similarity_threshold:
                    book_id = book_ids[i]
                    book_info = books_data[book_id]
                    
                    # スニペット生成もトレース
                    with tracer.start_as_current_span("generate_snippet", attributes={"book.id": book_id}):
                        snippet = get_snippet(book_info['raw_text'], query)
                    
                    results.append({
                        'id': book_id,
                        'title': book_info['title'],
                        'author': book_info['author'],
                        'score': float(similarity),
                        'snippet': snippet,
                        'search_method': 'tfidf'
                    })
            
            # スコア順にソートして上位結果を返す
            results.sort(key=lambda x: x['score'], reverse=True)
            final_results = results[:max_results]
            
            results_span.set_attribute("results.total_matches", len(results))
            results_span.set_attribute("results.returned", len(final_results))
            span.set_attribute("search.results_count", len(final_results))
            
            if final_results:
                span.set_attribute("search.top_score", final_results[0]['score'])
                span.set_attribute("search.lowest_score", final_results[-1]['score'])
            
            return final_results

def bm25_search(query: str, max_results: int = 20, score_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """BM25ベースの検索を実行
    
    Args:
        query: 検索クエリ
        max_results: 最大結果件数
        score_threshold: BM25スコアの閾値
        
    Returns:
        検索結果のリスト
    """
    with tracer.start_as_current_span("bm25_search") as span:
        span.set_attribute("search.query", query)
        span.set_attribute("search.max_results", max_results)
        span.set_attribute("search.score_threshold", score_threshold)
        span.set_attribute("search.algorithm", "bm25")
        
        # クエリの前処理
        with tracer.start_as_current_span("preprocess_query") as preprocess_span:
            processed_query = preprocess_text(query)
            query_tokens = processed_query.split()
            preprocess_span.set_attribute("query.original", query)
            preprocess_span.set_attribute("query.processed", processed_query)
            preprocess_span.set_attribute("query.tokens_count", len(query_tokens))
            
            if not query_tokens:
                span.set_attribute("search.results_count", 0)
                return []
        
        # BM25スコア計算
        with tracer.start_as_current_span("compute_bm25_scores") as bm25_span:
            scores = bm25_model.get_scores(query_tokens)
            bm25_span.set_attribute("bm25.scores_computed", len(scores))
            bm25_span.set_attribute("bm25.max_score", float(max(scores)) if len(scores) > 0 else 0)
            bm25_span.set_attribute("bm25.min_score", float(min(scores)) if len(scores) > 0 else 0)
        
        # 結果の整理
        with tracer.start_as_current_span("process_results") as results_span:
            results = []
            book_ids = list(books_data.keys())
            
            for i, score in enumerate(scores):
                if score > score_threshold:
                    book_id = book_ids[i]
                    book_info = books_data[book_id]
                    
                    # スニペット生成もトレース
                    with tracer.start_as_current_span("generate_snippet", attributes={"book.id": book_id}):
                        snippet = get_snippet(book_info['raw_text'], query)
                    
                    results.append({
                        'id': book_id,
                        'title': book_info['title'],
                        'author': book_info['author'],
                        'score': float(score),
                        'snippet': snippet,
                        'search_method': 'bm25'
                    })
            
            # スコア順にソートして上位結果を返す
            results.sort(key=lambda x: x['score'], reverse=True)
            final_results = results[:max_results]
            
            results_span.set_attribute("results.total_matches", len(results))
            results_span.set_attribute("results.returned", len(final_results))
            span.set_attribute("search.results_count", len(final_results))
            
            if final_results:
                span.set_attribute("search.top_score", final_results[0]['score'])
                span.set_attribute("search.lowest_score", final_results[-1]['score'])
            
            return final_results

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
    elif search_method == "bm25":
        return bm25_search(query, **kwargs)
    # elif search_method == "dense":
    #     return dense_search(query, **kwargs)
    else:
        raise ValueError(f"Unsupported search method: {search_method}")

@app.get("/search")
async def search_books(q: str, request: Request):
    """検索クエリに基づいて書籍を検索"""
    
    # HTTPヘッダーからトレースコンテキストを抽出
    context = propagate.extract(dict(request.headers))
    
    # 抽出されたコンテキストを使用してSpanを開始
    with tracer.start_as_current_span("search_api", context=context) as span:
        span.set_attribute("http.route", "/search")
        span.set_attribute("search.query", q)
        
        # 分散トレース情報をログ出力
        traceparent = request.headers.get('traceparent')
        tracestate = request.headers.get('tracestate')
        
        if traceparent:
            print(f"🔗 Received Distributed Trace: {traceparent}")
            if tracestate:
                print(f"   Trace State: {tracestate}")
            span.set_attribute("distributed.trace.received", True)
            span.set_attribute("distributed.trace.traceparent", traceparent)
        else:
            print("⚠️  No trace context received from frontend")
            span.set_attribute("distributed.trace.received", False)
        
        start_time = time.time()
        
        if not q or not q.strip():
            span.set_attribute("error.type", "validation_error")
            span.set_attribute("error.message", "空の検索クエリ")
            logger.warning("空の検索クエリ", extra={"event_type": "search_validation_error", "query": q})
            raise HTTPException(status_code=400, detail="検索クエリが空です")
        
        try:
            # フィーチャーフラグで検索アルゴリズムを決定
            search_method = "tfidf"  # デフォルト
            
            if unleash_client and unleash_client.is_enabled("bm25_search"):
                search_method = "bm25"
                print("🚀 Feature flag enabled: Using BM25 search algorithm")
                logger.info("フィーチャーフラグ有効", extra={"event_type": "feature_flag", "flag": "bm25_search", "enabled": True})
            else:
                print("📊 Feature flag disabled: Using TF-IDF search algorithm")
                logger.info("フィーチャーフラグ無効", extra={"event_type": "feature_flag", "flag": "bm25_search", "enabled": False})
            
            # 検索実行
            with tracer.start_as_current_span("perform_search") as search_span:
                search_span.set_attribute("search.method", search_method)
                search_span.set_attribute("feature_flag.bm25_enabled", search_method == "bm25")
                results = perform_search(q, search_method=search_method)
            
            response_time = time.time() - start_time
            
            # スパンに属性を追加
            span.set_attribute("search.results_count", len(results))
            span.set_attribute("search.response_time_ms", round(response_time * 1000, 3))
            span.set_attribute("http.status_code", 200)
            
            logger.info("検索API", extra={"event_type": "search_complete", "query": q, "results_count": len(results), "duration_ms": round(response_time * 1000, 3)})
            
            return {
                'query': q,
                'total_results': len(results),
                'results': results
            }
        except Exception as e:
            error_time = time.time() - start_time
            
            # エラー情報をスパンに記録
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.set_attribute("search.error_time_ms", round(error_time * 1000, 3))
            span.set_attribute("http.status_code", 500)
            
            logger.error("検索エラー", extra={"event_type": "search_error", "query": q, "error": str(e), "duration_ms": round(error_time * 1000, 3)})
            raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
