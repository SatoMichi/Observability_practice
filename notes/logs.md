# JSON構造化ログ実装の記録

## 概要
Gutenberg Explorer（書籍検索アプリ）にJSON構造化ログを実装した過程の記録。

**最終成果**: 標準`logging`モジュールを使用したシンプルで安定したJSON構造化ログシステム

---

## 実装の段階

### 第1段階: structlogによる初期実装 ❌

#### 試行内容
- `structlog==23.2.0`をrequirements.txtに追加
- 複雑なstructlog設定でJSON形式ログ実装を試行
- カスタムプロセッサとJSONフォーマッターの設定

#### 発生した問題
1. **設定の複雑さ**: 
   ```python
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
   ```

2. **TypeError発生**: 
   ```
   TypeError: BoundLogger.info() got multiple values for argument 'event'
   ```
   - structlogのAPIでキーワード引数の重複が発生
   - `logger.info("メッセージ", event="startup", message="メッセージ")`のような構文エラー

3. **ログが出力されない**: 
   - 起動イベントは実行されるが、JSON形式のログが表示されない
   - デバッグが困難

#### 修正の試み
- `event`キーワード引数を`event_type`に変更
- メッセージパラメータの重複を削除
- カスタムフォーマッターの簡略化

#### 結果
structlogでは安定した動作を実現できず、標準ライブラリへの移行を決定

---

### 第2段階: 標準loggingモジュールへの移行 ✅

#### 設計判断
**「単純にJSON形式のログを出力したいだけなら、標準的なPythonの`logging`モジュールで十分」**

#### 実装アプローチ
1. **カスタムFormatter作成**:
   ```python
   class JsonFormatter(logging.Formatter):
       def format(self, record):
           timestamp = datetime.now(timezone.utc).isoformat()
           log_record = {
               "timestamp": timestamp,
               "level": record.levelname,
               "event": getattr(record, 'event_type', 'unknown'),
               "message": record.getMessage()
           }
           # 追加フィールドをマージ
           return json.dumps(log_record, ensure_ascii=False, default=str)
   ```

2. **シンプルなロガー設定**:
   ```python
   logger = logging.getLogger("search_app")
   handler = logging.StreamHandler()
   handler.setFormatter(JsonFormatter())
   logger.addHandler(handler)
   ```

3. **extraパラメータによる構造化**:
   ```python
   logger.info("検索API", extra={
       "event_type": "search_complete", 
       "query": q, 
       "results_count": len(results), 
       "duration_ms": round(response_time * 1000, 3)
   })
   ```

#### 結果
✅ **即座に動作**: 初回実装で正常にJSON出力
✅ **安定性**: 複雑な設定エラーなし
✅ **理解しやすさ**: 標準ライブラリの知識で対応可能

---

### 第3段階: ログの最適化 📊

#### 問題: 過剰なログ出力
初期実装では冗長すぎるログが出力されていた：

**起動時**: 8つのログ + デバッグprint文
```json
{"event": "startup", "message": "アプリケーション起動開始"}
{"event": "data_loading", "message": "書籍データを読み込み中"} 
{"event": "books_discovery", "message": "利用可能な書籍数を確認", "books_available": 18}
{"event": "loading_progress", "message": "書籍読み込み進捗", "books_loaded": 5} // ×3回
{"event": "loading_complete", "message": "書籍読み込み完了"}
{"event": "tfidf_start", "message": "TF-IDFベクトル化を実行中"}
{"event": "tfidf_complete", "message": "TF-IDFベクトル化完了"}
{"event": "startup_complete", "message": "アプリケーション起動完了"}
```

#### 最適化方針
「重要な情報のみを残し、監視とデバッグに必要十分なログにする」

#### 削除したログ
- デバッグ用print文: `print("起動イベント開始")`
- 過剰な進捗ログ: 5冊ごとの書籍読み込み進捗
- 詳細すぎるログ: TF-IDFベクトル化の開始・完了
- 重複したログ: APIリクエスト受信 + レスポンス完了

#### 最適化後の結果
**起動時**: 2つのログのみ
```json
{"event": "startup", "message": "アプリケーション起動開始"}
{"event": "startup_complete", "message": "アプリケーション起動完了", "duration_seconds": 3.44, "books_count": 18}
```

**API処理**: 1つのログのみ
```json
{"event": "search_complete", "message": "検索API", "query": "love", "results_count": 10, "duration_ms": 403.427}
```

---

### 第4段階: リファクタリング（関心の分離） 🏗️

#### 目的
「ログ機能をモジュール化して、コードの保守性と再利用性を向上させる」

#### 実装
1. **新規モジュール作成**: `log_system.py`
   ```python
   """JSON構造化ログシステム"""
   
   class JsonFormatter(logging.Formatter):
       """JSON形式でログを出力するフォーマッター"""
   
   def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
       """JSON構造化ログ用のロガーを設定"""
   
   def get_logger(name: Optional[str] = None) -> logging.Logger:
       """既存のロガーを取得するか、新しいロガーを作成"""
   ```

2. **main.pyの簡素化**:
   ```python
   # ログ設定関連のコードを削除
   from log_system import setup_logger
   logger = setup_logger("search_app")
   ```

#### 構成比較
**分離前**: `main.py` (11.0KB, 326行)
- API実装 + ログ設定 + JSON formatter + ロガー設定が混在

**分離後**: 責任分離
- `main.py` (9.0KB, 258行): API実装に集中
- `log_system.py` (2.5KB, 82行): ログ機能専用モジュール

---

## 技術的な学び

### 1. ライブラリ選択の重要性 📚
- **複雑なライブラリ ≠ 良いソリューション**
- 要件に対して過剰な機能は逆に問題を生む
- 標準ライブラリの安定性と信頼性

### 2. 段階的な実装 🪜
- 小さく始めて、動作確認しながら拡張
- 一度に全てを実装せず、問題を分離して解決

### 3. 運用を考慮した設計 🎯
- ログ量とパフォーマンスのバランス
- 監視に必要な情報の取捨選択
- 可読性 vs 詳細性のトレードオフ

### 4. コード構造の重要性 🏗️
- 関心の分離による保守性向上
- モジュール化による再利用性
- テストしやすい設計

---

## 最終的な実装

### 出力例
```json
// 起動時
{"timestamp": "2025-06-24T03:32:02.557742+00:00", "level": "INFO", "event": "startup", "message": "アプリケーション起動開始", "taskName": "Task-2"}
{"timestamp": "2025-06-24T03:32:06.001749+00:00", "level": "INFO", "event": "startup_complete", "message": "アプリケーション起動完了", "taskName": "Task-2", "duration_seconds": 3.44, "books_count": 18}

// API処理
{"timestamp": "2025-06-24T03:30:29.766719+00:00", "level": "INFO", "event": "api_response", "message": "書籍一覧API", "taskName": "Task-3", "endpoint": "/books", "response_count": 18, "duration_ms": 0.005}
{"timestamp": "2025-06-24T03:30:30.186819+00:00", "level": "INFO", "event": "search_complete", "message": "検索API", "taskName": "Task-4", "query": "love", "results_count": 10, "duration_ms": 403.427}
```

### ファイル構成
```
backend/
├── main.py              # FastAPI application
├── log_system.py        # JSON logging system
├── requirements.txt     # Dependencies (no structlog)
└── Dockerfile          # Container configuration
```

### 依存関係
```txt
fastapi==0.104.1
uvicorn==0.24.0
nltk==3.8.1
scikit-learn==1.3.1
numpy==1.26.2
```

---

## まとめ

### 成果 ✅
- ✅ **安定性**: 標準ライブラリベースの確実な動作
- ✅ **シンプル**: 理解しやすく保守しやすいコード
- ✅ **効率性**: 必要十分なログ量でパフォーマンス影響最小
- ✅ **観測可能性**: 監視とデバッグに必要な構造化データ
- ✅ **拡張性**: モジュール化による再利用可能な設計

### 教訓 💡
1. **Keep It Simple**: 複雑なソリューションより、シンプルで動くものを選ぶ
2. **標準ライブラリの力**: 既存のツールを最大限活用する
3. **段階的改善**: 完璧を求めず、動くものから始めて改善する
4. **運用視点**: 開発時だけでなく、運用時の使いやすさを考慮する

この経験により、プロダクションレディなJSON構造化ログシステムが完成しました。🚀
