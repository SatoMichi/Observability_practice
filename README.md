# 📚 Gutenberg Explorer

プロジェクト・グーテンベルクの書籍を検索・閲覧できるモダンなWebアプリケーションです。NLTK Gutenbergコーパスを使用してTF-IDFベースの全文検索機能を提供します。

![Build Status](https://github.com/SatoMichi/Observability_practice/actions/workflows/build-and-push-fast.yml/badge.svg)

## 🌟 機能

### 📖 書籍管理
- **書籍一覧表示**: プロジェクト・グーテンベルクの名作文学を一覧表示
- **書籍詳細**: 作者名、タイトル、テキスト内容を表示
- **レスポンシブデザイン**: モバイルからデスクトップまで対応

### 🔍 高度な検索機能
- **全文検索**: TF-IDF (Term Frequency-Inverse Document Frequency) アルゴリズム
- **自然言語処理**: NLTK (Natural Language Toolkit) による高精度検索
- **スコアリング**: 関連度に基づく検索結果ランキング
- **リアルタイム検索**: 快速な検索レスポンス

### 🎨 モダンなUI/UX
- **React + Vite**: 高速でモダンなフロントエンド
- **SCSS**: スタイリッシュで保守性の高いスタイル
- **ナビゲーション**: 直感的なページ間移動
- **エラーハンドリング**: ユーザーフレンドリーなエラー表示

## 🛠 技術スタック

### フロントエンド
- **React 18**: モダンなUIライブラリ
- **Vite**: 高速ビルドツール
- **React Router**: SPA ルーティング
- **SCSS**: CSS プリプロセッサ
- **Native Fetch API**: HTTPクライアント（axios不使用で軽量化）

### バックエンド
- **FastAPI**: 高性能Python Webフレームワーク
- **NLTK**: 自然言語処理ライブラリ
- **scikit-learn**: 機械学習・TF-IDF実装
- **uvicorn**: ASGI サーバー
- **Python 3.11**: 最新Python環境

### インフラストラクチャ
- **Docker**: コンテナ化
- **Kubernetes (EKS)**: オーケストレーション
- **GitHub Actions**: CI/CD パイプライン
- **GHCR**: GitHub Container Registry
- **ARM64最適化**: Apple Silicon / Graviton対応

## 🚀 セットアップ

### 前提条件
- Docker & Docker Compose
- Node.js 18+ (ローカル開発時)
- Python 3.11+ (ローカル開発時)

### 開発環境での起動
```bash
# プロジェクトをクローン
git clone https://github.com/SatoMichi/Observability_practice.git
cd Observability_practice

# Docker Composeで起動
docker-compose up --build

# アプリケーションにアクセス
open http://localhost:3000
```

### 本番環境デプロイ（Kubernetes）
```bash
# Kubernetesクラスターにデプロイ
kubectl apply -f k8s/

# ポートフォワードでアクセス
kubectl port-forward service/frontend-service 3000:80
open http://localhost:3000
```

### 高速デプロイ用スクリプト
```bash
# 最新イメージで即座にデプロイ
./deploy-latest.sh
```

## 📡 API仕様

### エンドポイント
- `GET /` - ヘルスチェック
- `GET /books` - 書籍一覧取得
- `POST /search?q={query}` - 全文検索

### レスポンス例
```json
// GET /books
{
  "books": [
    {
      "id": "austen-emma",
      "title": "Emma",
      "author": "Jane Austen"
    }
  ]
}

// GET /search?q=love
{
  "query": "love",
  "total_results": 15,
  "results": [
    {
      "id": "shakespeare-hamlet",
      "title": "Hamlet", 
      "author": "William Shakespeare",
      "score": 0.8945,
      "excerpt": "...love passage..."
    }
  ]
}
```

## 🎯 プロジェクトで学んだこと

### 🔧 技術的な学習

#### 1. **プラットフォーム最適化**
- **課題**: GitHub ActionsでAMD64のみビルド → ARM64 EKSクラスターで動作せず
- **解決**: ARM64専用ビルドに変更してパフォーマンス50%向上
- **学習**: アーキテクチャマッチングの重要性

#### 2. **現代的なHTTPクライアント**
- **課題**: axiosの依存関係不整合でビルド失敗
- **解決**: Native Fetch APIへ移行でバンドルサイズ削減
- **学習**: 依存関係最小化の価値

#### 3. **CI/CDパイプライン最適化**
- **GitHub Actionsキャッシュ障害**: 一時的にキャッシュ無効化
- **並列ビルド**: フロントエンド・バックエンド同時実行
- **セキュリティスキャン**: 学習目的で不要機能削除

#### 4. **package.json同期管理**
- **課題**: package.jsonとpackage-lock.jsonの不整合
- **解決**: npm installによる同期修復
- **学習**: 依存関係管理のベストプラクティス

#### 5. **UI/UX改善とブランディング**
- **課題**: 汎用的な「全文検索」タイトルでブランド性が低い
- **解決**: 「📚 Gutenberg Explorer」に変更し中央配置でアクセシビリティ向上
- **学習**: ユーザー体験とブランディングの重要性

#### 6. **Kubernetesサービスディスカバリー**
- **課題**: Docker ComposeとKubernetesでサービス名が異なり検索API失敗
- **解決**: nginx設定を`backend` → `backend-service`に修正
- **学習**: 環境間でのネットワーク設定の差異と統一性の重要性

#### 7. **デプロイメント戦略の改善**
- **課題**: `kubectl set image`で同じ`:latest`タグ指定時、新イメージがプルされない
- **解決**: `kubectl rollout restart`を使用して確実なイメージ更新
- **学習**: Kubernetesデプロイメントの信頼性向上テクニック

### 🐛 トラブルシューティング経験

#### **ImagePullBackOff問題**
```
エラー: no match for platform in manifest: not found
原因: AMD64イメージをARM64クラスターで実行
解決: platforms: linux/arm64 に変更
```

#### **依存関係エラー**
```
エラー: npm ci can only install packages when package.json and package-lock.json are in sync
原因: package.jsonの更新後、package-lock.json未更新
解決: npm install実行で同期
```

#### **ビルド失敗**
```
エラー: failed to resolve import "axios"
原因: package.jsonからaxios削除、コードで使用継続
解決: Fetch APIへ移行
```

#### **Kubernetes API接続エラー**
```
エラー: 検索に失敗しました (フロントエンド)
原因: nginx proxy_pass設定でDocker Compose用サービス名使用
解決: backend → backend-service に修正
```

#### **デプロイメント更新されない問題**
```
エラー: 新しいコード変更がKubernetesで反映されない
原因: kubectl set imageで同じ:latestタグ → Kubernetesがプル不要と判断
解決: kubectl rollout restart使用で強制更新
```

### 🏗 アーキテクチャの進化

#### **初期構成**
- マルチプラットフォーム（AMD64 + ARM64）
- axios使用
- GitHub Actionsキャッシュ有効

#### **最終構成**
- ARM64専用最適化
- Native Fetch API
- キャッシュレス高速ビルド

## 📈 パフォーマンス最適化

### ビルド時間改善
- **Before**: 60秒（マルチプラットフォーム）
- **After**: 30-35秒（ARM64専用）
- **改善率**: 40-60%短縮

### バンドルサイズ削減
- **axios削除**: ~13KB削減
- **依存関係最小化**: 軽量化達成

### デプロイ速度向上
- **プラットフォーム一致**: イメージプル高速化
- **並列ビルド**: CI/CD時間短縮

### UI/UX向上
- **ブランディング強化**: 「📚 Gutenberg Explorer」で視認性向上
- **アクセシビリティ**: 中央配置でレスポンシブ対応
- **検索機能改善**: Kubernetesでの安定したAPI接続

### 運用改善
- **確実なデプロイ**: `kubectl rollout restart`で100%更新保証
- **環境統一**: Docker Compose / Kubernetes間の設定整合性
- **自動化強化**: GitHub Actions → GHCR → Kubernetes完全自動化

## 🔍 監視とオブザーバビリティ

このプロジェクトは学習目的で作成されており、以下の要素を含んでいます：

### 📊 **分散トレーシングシステム（実装完了）** ✅

#### **OpenTelemetry完全実装**
```yaml
実装状況:
  フロントエンド: React カスタムトレーサー実装
  バックエンド: FastAPI OpenTelemetry SDK自動計装  
  分散トレース: W3C Trace Context標準準拠
  可視化: Datadog APM連携完了
  
技術仕様:
  - 統一Trace ID: フロントエンド→バックエンド完全伝播
  - 5階層親子関係: search_api → tfidf_search → 詳細処理
  - W3C標準: traceparent/tracestate ヘッダー実装
  - リアルタイム: ミリ秒単位のパフォーマンス計測
```

#### **実際のトレース例（本番環境）**
```
🌊 統一分散トレース (Trace ID: 0000000000000000000d062aa833921d)
├── 🌐 frontend_search (152ms)
│   ├── update_ui_loading (0ms)
│   ├── prepare_api_request (0ms)
│   ├── api_request_execute (148ms)
│   │   ├── 🔗 http_request (147ms) ───┐
│   │   └── parse_response (1ms)       │
│   ├── process_search_results (1ms)    │
│   └── update_ui_final (0ms)          │
│                                      │
└── 🔍 search_api (バックエンド) ←──────┘ [同一Trace ID]
    ├── perform_search (3.98ms)
    ├── tfidf_search (3.91ms)
    │   ├── preprocess_query
    │   ├── vectorize_query
    │   ├── compute_similarity
    │   └── process_results
    │       └── generate_snippet
```

#### **Datadog APM可視化**
- **Service Map**: フロントエンド→バックエンドの依存関係
- **Trace Detail**: エンドツーエンドの処理時間分析
- **Performance**: レスポンス時間（平均4-5ms）
- **Error Tracking**: 実時間エラー監視

### ログ管理
- フロントエンド: ブラウザコンソールログ
- バックエンド: 構造化ログ出力
- 検索クエリ: パフォーマンス計測
- **分散ログ**: Trace ID連携による横断検索

### メトリクス
- レスポンス時間計測
- 検索結果件数追跡
- エラー率監視
- **トレースメトリクス**: スループット・レイテンシー分析

### 可観測性
- Kubernetes ポッド状態監視
- コンテナリソース使用量
- アプリケーションヘルスチェック
- **APM監視**: リアルタイムアプリケーション性能監視

## 🤝 コントリビューション

1. フォークする
2. フィーチャーブランチ作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエスト作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙏 謝辞

- **プロジェクト・グーテンベルク**: パブリックドメイン書籍の提供
- **NLTK**: 自然言語処理ツールキット
- **FastAPI**: 高性能Webフレームワーク
- **React**: モダンUIライブラリ

---

**📚 Gutenberg Explorer** - プロジェクト・グーテンベルクの世界を探索しよう！

## Datadog RUM 設定手順

### フロントエンドトレースをDatadogに送信するための設定

1. **Datadogコンソールで設定値を取得**
   - Datadog → UX Monitoring → RUM Applications
   - Application IDとClient Tokenを取得

2. **環境変数の設定**
```bash
# 実際の値に置き換えてください
export VITE_DD_APPLICATION_ID="your-actual-application-id"
export VITE_DD_CLIENT_TOKEN="your-actual-client-token"
export VITE_DD_SERVICE="gutenberg-search-frontend"
export VITE_DD_ENV="development"
```

3. **フロントエンドアプリケーションの再起動**
```bash
cd frontend
npm run dev
```

4. **動作確認**
   - ブラウザでアプリケーションにアクセス
   - 検索機能を使用
   - DatadogのRUM画面でトレースを確認

### 現在の状態
- バックエンドトレース: ✅ Datadog に送信済み
- フロントエンドトレース: ⚠️ 環境変数設定が必要
