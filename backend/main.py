import json
import string
import time
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# BM25 search algorithm
from rank_bm25 import BM25Okapi

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry import propagate
import logging

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
class SimpleConsoleSpanExporter:
    """簡易的なコンソール出力エクスポーター"""
    def export(self, spans):
        for span in spans:
            print(f"🔍 Span: {span.name}")
            print(f"   Service: {span.resource.attributes.get('service.name', 'unknown')}")
            print(f"   Trace ID: {format(span.context.trace_id, '032x')}")
            print(f"   Span ID: {format(span.context.span_id, '016x')}")
            print(f"   Duration: {(span.end_time - span.start_time) / 1_000_000:.2f} ms")
            
            # 分散トレース情報の表示
            distributed_received = span.attributes.get('distributed.trace.received', False)
            if distributed_received:
                traceparent = span.attributes.get('distributed.trace.traceparent', '')
                print(f"   🔗 Distributed Trace: Connected from Frontend")
                print(f"   📡 Traceparent: {traceparent}")
            
            if span.attributes:
                print(f"   Attributes: {dict(span.attributes)}")
            print()
        return 0
    
    def shutdown(self):
        """エクスポーターのシャットダウン"""
        print("🔍 Console Span Exporter shutdown")
        return True

def setup_tracing():
    """OpenTelemetryトレースの初期化"""
    import os
    
    # 環境に応じたサービス名とリソース設定
    service_name = os.getenv("OTEL_SERVICE_NAME", "gutenberg-search-api")
    service_version = os.getenv("DD_VERSION", "1.0.0")
    environment = os.getenv("DD_ENV", "development")
    
    # リソースの設定
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment
    })
    
    # TracerProviderの設定
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # エクスポーターの設定
    # 簡易コンソール出力（開発・デバッグ用）
    console_exporter = SimpleConsoleSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Kubernetes環境での分散トレース設定
    dd_trace_agent_url = os.getenv("DD_TRACE_AGENT_URL")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    
    # Datadog環境でのOTLP設定
    if dd_trace_agent_url:
        try:
            # Datadog Agent経由でのトレース送信
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPOTLPSpanExporter
            
            # Datadog Agent OTLPエンドポイント使用
            dd_otlp_endpoint = dd_trace_agent_url.replace(":8126", ":4318")
            otlp_exporter = HTTPOTLPSpanExporter(
                endpoint=f"{dd_otlp_endpoint}/v1/traces",
                headers={}
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            print(f"🐕 Datadog OTLP Exporter configured: {dd_otlp_endpoint}")
            
        except Exception as e:
            print(f"⚠️  Datadog OTLP Exporter setup failed: {e}")
            # フォールバック: 標準OTLPエンドポイント
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPOTLPSpanExporter
                otlp_exporter = HTTPOTLPSpanExporter(
                    endpoint=f"{otlp_endpoint}/v1/traces",
                    headers={}
                )
                tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                print(f"🔗 Fallback OTLP Exporter configured: {otlp_endpoint}")
            except Exception as fallback_error:
                print(f"⚠️  Fallback OTLP Exporter setup failed: {fallback_error}")
                print("   Continuing with console output only...")
    else:
        # ローカル環境用の設定（一時的に無効化）
        print(f"💡 OTLP送信を無効化（開発モード）")
        print(f"   コンソール出力のみでトレーシング実行中...")
        # try:
        #     from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPOTLPSpanExporter
        #     otlp_exporter = HTTPOTLPSpanExporter(
        #         endpoint=f"{otlp_endpoint}/v1/traces",
        #         headers={}
        #     )
        #     tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        #     print(f"🔗 Local OTLP Exporter configured: {otlp_endpoint}")
        # except Exception as e:
        #     print(f"⚠️  Local OTLP Exporter setup failed: {e}")
        #     print("   Continuing with console output only...")
    
    return trace.get_tracer(__name__)

# トレーサーの初期化
tracer = setup_tracing()

# ロガーの設定
logger = setup_logger("search_app")

app = FastAPI(title="全文検索API")

# FastAPIの自動計装を有効化
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
bm25_index = None

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
    global books_data, tfidf_vectorizer, tfidf_matrix, processed_texts, bm25_index
    
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

            # BM25インデックス構築
            with tracer.start_as_current_span("bm25_indexing") as bm25_span:
                print(f"📊 BM25インデックス構築を開始...")
                bm25_start = time.time()
                
                # BM25用のトークン化されたテキスト準備
                tokenized_texts = []
                for text in processed_texts.values():
                    tokenized_texts.append(text.split())
                
                # BM25インデックス構築
                bm25_index = BM25Okapi(tokenized_texts)
                
                bm25_time = time.time() - bm25_start
                print(f"📊 BM25インデックス構築完了: {bm25_time:.2f}秒")
                print(f"   平均文書長: {bm25_index.avgdl:.1f}トークン")
                print(f"   総文書数: {len(tokenized_texts)}件")
                
                bm25_span.set_attribute("bm25.duration_seconds", round(bm25_time, 2))
                bm25_span.set_attribute("bm25.documents_count", len(tokenized_texts))
                bm25_span.set_attribute("bm25.average_doc_length", round(bm25_index.avgdl, 2))
                bm25_span.set_attribute("bm25.total_tokens", sum(len(doc) for doc in tokenized_texts))
            
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
                        'snippet': snippet
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

def bm25_search(query: str, max_results: int = 20, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """BM25ベースの検索を実行（TF-IDFより高精度）
    
    Args:
        query: 検索クエリ
        max_results: 最大結果件数
        score_threshold: スコアの閾値
        
    Returns:
        検索結果のリスト
    """
    with tracer.start_as_current_span("bm25_search") as span:
        span.set_attribute("search.query", query)
        span.set_attribute("search.max_results", max_results)
        span.set_attribute("search.score_threshold", score_threshold)
        span.set_attribute("search.algorithm", "BM25")
        
        # クエリの前処理
        with tracer.start_as_current_span("preprocess_query") as preprocess_span:
            processed_query = preprocess_text(query)
            preprocess_span.set_attribute("query.original", query)
            preprocess_span.set_attribute("query.processed", processed_query)
            
            if not processed_query:
                span.set_attribute("search.results_count", 0)
                return []
            
            # BM25用にトークン化
            query_tokens = processed_query.split()
            preprocess_span.set_attribute("query.tokens", query_tokens)
            preprocess_span.set_attribute("query.token_count", len(query_tokens))
        
        # BM25スコア計算
        with tracer.start_as_current_span("compute_bm25_scores") as bm25_span:
            scores = bm25_index.get_scores(query_tokens)
            bm25_span.set_attribute("bm25.scores_count", len(scores))
            bm25_span.set_attribute("bm25.max_score", float(max(scores)) if len(scores) > 0 else 0.0)
            bm25_span.set_attribute("bm25.min_score", float(min(scores)) if len(scores) > 0 else 0.0)
        
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
                        'snippet': snippet
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
            
            logger.info("BM25検索完了", extra={
                "event_type": "bm25_search_complete", 
                "query": query,
                "results_count": len(final_results),
                "total_matches": len(results),
                "top_score": final_results[0]['score'] if final_results else 0.0
            })
            
            return final_results

def slow_tfidf_search(query: str, max_results: int = 20, similarity_threshold: float = 0.01) -> List[Dict[str, Any]]:
    """意図的に遅いTF-IDFベースの検索（オブザーバビリティー研修用）
    
    Args:
        query: 検索クエリ
        max_results: 最大結果件数
        similarity_threshold: 類似度の閾値
        
    Returns:
        検索結果のリスト
    """
    with tracer.start_as_current_span("slow_tfidf_search") as span:
        span.set_attribute("search.query", query)
        span.set_attribute("search.max_results", max_results)
        span.set_attribute("search.similarity_threshold", similarity_threshold)
        span.set_attribute("search.algorithm", "SLOW_TFIDF")
        
        # ボトルネック1: 前処理で無駄な処理
        with tracer.start_as_current_span("slow_preprocess_query") as preprocess_span:
            processed_query = preprocess_text(query)
            preprocess_span.set_attribute("query.original", query)
            preprocess_span.set_attribute("query.processed", processed_query)
            
            if not processed_query:
                span.set_attribute("search.results_count", 0)
                return []
            
            # 無駄な文字列処理ループ（ボトルネック）
            dummy_operations = 0
            for i in range(50000):  # 5万回の無駄なループ
                temp_string = processed_query.upper().lower().strip()
                dummy_operations += len(temp_string)
            
            preprocess_span.set_attribute("bottleneck.dummy_operations", dummy_operations)
            time.sleep(0.2)  # 200ms の意図的な遅延
        
        # ボトルネック2: ベクトル化で重複処理
        with tracer.start_as_current_span("slow_vectorize_query") as vector_span:
            # 通常のベクトル化
            query_vector = tfidf_vectorizer.transform([processed_query])
            vector_span.set_attribute("vector.shape", str(query_vector.shape))
            
            # 無駄な重複ベクトル化（ボトルネック）
            for i in range(10):  # 10回重複してベクトル化
                duplicate_vector = tfidf_vectorizer.transform([processed_query])
                time.sleep(0.05)  # 各回50ms遅延
            
            vector_span.set_attribute("bottleneck.duplicate_vectorizations", 10)
        
        # ボトルネック3: 類似度計算で非効率な処理
        with tracer.start_as_current_span("slow_compute_similarity") as similarity_span:
            # 通常の類似度計算
            similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
            similarity_span.set_attribute("similarity.matrix_size", len(similarities))
            
            # 無駄な類似度再計算（ボトルネック）
            recalculation_count = 0
            for i in range(5):  # 5回無駄に再計算
                temp_similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
                recalculation_count += len(temp_similarities)
                time.sleep(0.1)  # 各回100ms遅延
            
            similarity_span.set_attribute("bottleneck.recalculation_operations", recalculation_count)
        
        # ボトルネック4: 結果処理で非効率なソート
        with tracer.start_as_current_span("slow_process_results") as results_span:
            results = []
            book_ids = list(books_data.keys())
            
            for i, similarity in enumerate(similarities):
                if similarity > similarity_threshold:
                    book_id = book_ids[i]
                    book_info = books_data[book_id]
                    
                    # スニペット生成（通常処理）
                    with tracer.start_as_current_span("slow_generate_snippet", attributes={"book.id": book_id}):
                        snippet = get_snippet(book_info['raw_text'], query)
                        # 各スニペット生成後に遅延
                        time.sleep(0.03)  # 30ms遅延
                    
                    results.append({
                        'id': book_id,
                        'title': book_info['title'],
                        'author': book_info['author'],
                        'score': float(similarity),
                        'snippet': snippet
                    })
            
            # 非効率なバブルソート（ボトルネック）
            with tracer.start_as_current_span("inefficient_bubble_sort") as sort_span:
                # まず通常のソート（これは隠す）
                results.sort(key=lambda x: x['score'], reverse=True)
                
                # その後、教育目的で見えるバブルソート（実際は何もしない）
                n = len(results)
                bubble_comparisons = 0
                for i in range(min(n, 50)):  # 最大50要素まで
                    for j in range(min(n-i-1, 50)):
                        bubble_comparisons += 1
                        # 実際の交換はしない（結果は変わらないように）
                        time.sleep(0.001)  # 1ms遅延
                
                sort_span.set_attribute("bottleneck.bubble_sort_comparisons", bubble_comparisons)
            
            final_results = results[:max_results]
            
            results_span.set_attribute("results.total_matches", len(results))
            results_span.set_attribute("results.returned", len(final_results))
            span.set_attribute("search.results_count", len(final_results))
            
            if final_results:
                span.set_attribute("search.top_score", final_results[0]['score'])
                span.set_attribute("search.lowest_score", final_results[-1]['score'])
            
            logger.info("遅いTF-IDF検索完了", extra={
                "event_type": "slow_tfidf_search_complete", 
                "query": query,
                "results_count": len(final_results),
                "total_matches": len(results),
                "top_score": final_results[0]['score'] if final_results else 0.0,
                "bottlenecks_included": ["slow_preprocessing", "duplicate_vectorization", "similarity_recalculation", "bubble_sort"]
            })
            
            return final_results

def perform_search(query: str, search_method: str = "tfidf", **kwargs) -> List[Dict[str, Any]]:
    """検索を実行する統合インターフェース
    
    Args:
        query: 検索クエリ
        search_method: 検索手法 ("tfidf", "bm25", "boolean", "fuzzy" など)
        **kwargs: 各検索手法固有のパラメータ
        
    Returns:
        検索結果のリスト
    """
    with tracer.start_as_current_span("perform_search_unified") as span:
        span.set_attribute("search.method", search_method)
        span.set_attribute("search.query", query)
        
        if search_method == "tfidf":
            return tfidf_search(query, **kwargs)
        elif search_method == "bm25":
            return bm25_search(query, **kwargs)
        elif search_method == "slow_tfidf":
            return slow_tfidf_search(query, **kwargs)
        # elif search_method == "boolean":
        #     return boolean_search(query, **kwargs)
        # elif search_method == "fuzzy":
        #     return fuzzy_search(query, **kwargs)
        else:
            available_methods = ["tfidf", "bm25", "slow_tfidf"]
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unsupported search method: {search_method}"))
            raise ValueError(f"Unsupported search method: {search_method}. Available methods: {available_methods}")

@app.get("/search")
async def search_books(q: str, method: str = "tfidf", request: Request = None):
    """検索クエリに基づいて書籍を検索
    
    Args:
        q: 検索クエリ
        method: 検索手法 ("tfidf" or "bm25")
        request: HTTPリクエスト
    """
    
    # HTTPヘッダーからトレースコンテキストを抽出
    context = propagate.extract(dict(request.headers))
    
    # 抽出されたコンテキストを使用してSpanを開始
    with tracer.start_as_current_span("search_api", context=context) as span:
        span.set_attribute("http.route", "/search")
        span.set_attribute("search.query", q)
        span.set_attribute("search.method", method)
        
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
            # 検索実行
            with tracer.start_as_current_span("perform_search") as search_span:
                search_span.set_attribute("search.method", method)
                results = perform_search(q, search_method=method)
            
            response_time = time.time() - start_time
            
            # スパンに属性を追加
            span.set_attribute("search.results_count", len(results))
            span.set_attribute("search.response_time_ms", round(response_time * 1000, 3))
            span.set_attribute("http.status_code", 200)
            
            logger.info("検索API", extra={"event_type": "search_complete", "query": q, "results_count": len(results), "duration_ms": round(response_time * 1000, 3)})
            
            return {
                'query': q,
                'method': method,
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

@app.get("/search/compare")
async def compare_search_methods(q: str, request: Request = None):
    """TF-IDFとBM25の検索結果を比較
    
    Args:
        q: 検索クエリ
        request: HTTPリクエスト
    """
    
    # HTTPヘッダーからトレースコンテキストを抽出
    context = propagate.extract(dict(request.headers)) if request else {}
    
    with tracer.start_as_current_span("search_compare_api", context=context) as span:
        span.set_attribute("http.route", "/search/compare")
        span.set_attribute("search.query", q)
        
        start_time = time.time()
        
        if not q or not q.strip():
            span.set_attribute("error.type", "validation_error")
            span.set_attribute("error.message", "空の検索クエリ")
            raise HTTPException(status_code=400, detail="検索クエリが空です")
        
        try:
            # 並列で両方の検索を実行
            with tracer.start_as_current_span("compare_searches") as compare_span:
                
                # TF-IDF検索
                with tracer.start_as_current_span("tfidf_comparison"):
                    tfidf_start = time.time()
                    tfidf_results = perform_search(q, search_method="tfidf")
                    tfidf_time = time.time() - tfidf_start
                
                # BM25検索
                with tracer.start_as_current_span("bm25_comparison"):
                    bm25_start = time.time()
                    bm25_results = perform_search(q, search_method="bm25")
                    bm25_time = time.time() - bm25_start
                
                compare_span.set_attribute("tfidf.results_count", len(tfidf_results))
                compare_span.set_attribute("tfidf.duration_ms", round(tfidf_time * 1000, 3))
                compare_span.set_attribute("bm25.results_count", len(bm25_results))
                compare_span.set_attribute("bm25.duration_ms", round(bm25_time * 1000, 3))
            
            response_time = time.time() - start_time
            
            span.set_attribute("search.total_time_ms", round(response_time * 1000, 3))
            span.set_attribute("http.status_code", 200)
            
            logger.info("検索比較API", extra={
                "event_type": "search_compare_complete", 
                "query": q,
                "tfidf_results": len(tfidf_results),
                "bm25_results": len(bm25_results),
                "duration_ms": round(response_time * 1000, 3)
            })
            
            return {
                'query': q,
                'comparison': {
                    'tfidf': {
                        'method': 'tfidf',
                        'total_results': len(tfidf_results),
                        'duration_ms': round(tfidf_time * 1000, 3),
                        'results': tfidf_results[:10]  # 上位10件のみ返す
                    },
                    'bm25': {
                        'method': 'bm25',
                        'total_results': len(bm25_results),
                        'duration_ms': round(bm25_time * 1000, 3),
                        'results': bm25_results[:10]  # 上位10件のみ返す
                    }
                },
                'performance': {
                    'faster_method': 'tfidf' if tfidf_time < bm25_time else 'bm25',
                    'speed_difference_ms': round(abs(tfidf_time - bm25_time) * 1000, 3)
                }
            }
            
        except Exception as e:
            error_time = time.time() - start_time
            
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.set_attribute("search.error_time_ms", round(error_time * 1000, 3))
            span.set_attribute("http.status_code", 500)
            
            logger.error("検索比較エラー", extra={"event_type": "search_compare_error", "query": q, "error": str(e), "duration_ms": round(error_time * 1000, 3)})
            raise HTTPException(status_code=500, detail=f"検索比較エラー: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
