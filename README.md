# 全文検索アプリケーション

[![Build and Push](https://github.com/SatoMichi/Observability_practice/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/SatoMichi/Observability_practice/actions/workflows/build-and-push.yml)

React + FastAPI構成の全文検索アプリケーションです。NLTK Gutenbergコーパスを使用してTF-IDFベースの検索機能を提供します。

## 🚀 機能

- **書籍一覧**: Gutenbergコーパスの書籍を一覧表示
- **全文検索**: TF-IDFベクトル化による高精度な類似度検索
- **スニペット表示**: 検索語を含む文脈の抜粋表示
- **ハイライト**: 検索結果内の検索語をハイライト表示
- **レスポンシブデザイン**: モバイル・デスクトップ対応

## 🏗️ アーキテクチャ

### バックエンド
- **FastAPI**: Python製の高速なWebフレームワーク
- **NLTK**: 自然言語処理ライブラリ（Gutenbergコーパス）
- **Scikit-learn**: TF-IDF ベクトル化とコサイン類似度計算

### フロントエンド
- **React 18**: モダンなUIライブラリ
- **Vite**: 高速なビルドツール
- **React Router**: SPA ルーティング
- **Axios**: HTTP クライアント
- **SCSS**: モジュラーなCSS設計（BEM方式）

## 📁 プロジェクト構成

```
Observability_SampleApp/
├── backend/
│   ├── main.py                 # FastAPI アプリケーション
│   ├── requirements.txt        # Python 依存関係
│   ├── Dockerfile              # バックエンド用 Docker 設定
│   └── .dockerignore           # Docker ビルド除外設定
├── frontend/
│   ├── src/
│   │   ├── components/         # 再利用可能コンポーネント
│   │   │   ├── Navbar/         # ナビゲーションバー
│   │   │   ├── BookCard/       # 書籍カード表示
│   │   │   ├── SearchForm/     # 検索フォーム
│   │   │   ├── SearchResult/   # 検索結果アイテム
│   │   │   ├── LoadingSpinner/ # ローディング表示
│   │   │   └── ErrorMessage/   # エラーメッセージ
│   │   ├── pages/              # ページコンポーネント
│   │   │   ├── Books/          # 書籍一覧ページ
│   │   │   └── Search/         # 検索ページ
│   │   ├── config/             # 設定ファイル
│   │   │   └── api.js          # API エンドポイント設定
│   │   ├── App.jsx             # メインアプリケーション
│   │   └── main.jsx            # エントリーポイント
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile              # フロントエンド用 Docker 設定
│   ├── nginx.conf              # nginx 設定（SPA + API プロキシ）
│   └── .dockerignore           # Docker ビルド除外設定
├── docker-compose.yml          # Docker Compose 設定
├── .github/workflows/          # GitHub Actions CI/CD
├── k8s/                        # Kubernetes マニフェスト
├── .dockerignore               # プロジェクト全体の除外設定
└── README.md
```

## 🐳 CI/CD

GitHub Actionsによる自動化されたワークフロー:
- **マルチプラットフォームビルド**: linux/amd64, linux/arm64
- **自動プッシュ**: GitHub Container Registry (GHCR)
- **セキュリティスキャン**: Trivy による脆弱性検査
- **キャッシュ最適化**: 高速ビルドのためのレイヤーキャッシュ

### コンテナイメージ
- **Backend**: `ghcr.io/satomichi/observability-backend:latest`
- **Frontend**: `ghcr.io/satomichi/observability-frontend:latest`

### 開発フロー
```bash
# 1. 開発・コミット
git add .
git commit -m "Add new feature"
git push origin main

# 2. GitHub Actions が自動実行
# - マルチプラットフォームビルド
# - GHCR自動プッシュ
# - セキュリティスキャン

# 3. 手動デプロイ (必要に応じて)
kubectl rollout restart deployment/backend -n satomichi
kubectl rollout restart deployment/frontend -n satomichi
```

## 📦 起動方法

### 前提条件
- Python 3.8+
- Node.js 16+
- npm または yarn
- Docker & Docker Compose (Docker利用時)

### 🐳 Docker Compose での起動（推奨）

```bash
# アプリケーションの起動（初回は自動ビルド）
docker-compose up -d

# ステータス確認
docker-compose ps

# ログ確認
docker-compose logs -f

# 停止
docker-compose down

# 再ビルドが必要な場合
docker-compose build --no-cache
```

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **API（プロキシ経由）**: http://localhost:3000/api/*

### 🔧 ローカル開発での起動

### 1. バックエンドの起動

```bash
# 依存関係のインストール
cd backend
pip install -r requirements.txt

# サーバーの起動
python main.py
```

バックエンドは `http://localhost:8000` で起動します。
初回起動時はNLTKデータのダウンロードとTF-IDFベクトルの生成が行われるため、時間がかかります。

### 2. フロントエンドの起動

```bash
# 依存関係のインストール
cd frontend
npm install

# 開発サーバーの起動
npm run dev
```

フロントエンドは `http://localhost:5173` で起動します。

## 🧪 テスト・動作確認

### 起動確認

```bash
# Docker Compose起動
docker-compose up -d

# コンテナ状態確認
docker-compose ps
# 両方のコンテナが "healthy" になるまで待機

# ログ確認
docker-compose logs backend
docker-compose logs frontend
```

### APIエンドポイントのテスト

```bash
# 書籍一覧の取得（18冊が返されること）
curl http://localhost:8000/books | jq '.books | length'

# 検索テスト（"love"で検索結果があること）
curl "http://localhost:8000/search?q=love" | jq '.total_results'

# プロキシ経由のテスト（Docker環境での統合テスト）
curl http://localhost:3000/api/books | jq '.books | length'
curl "http://localhost:3000/api/search?q=love" | jq '.total_results'
```

### ヘルスチェック

```bash
# バックエンドヘルスチェック
curl http://localhost:8000/books

# フロントエンドヘルスチェック
curl http://localhost:3000/health
```

### フロントエンド動作確認

- **ブラウザアクセス**: http://localhost:3000
- **書籍一覧ページ**: 18冊のGutenberg書籍が表示される
- **検索ページ**: 検索語入力で結果が表示される
- **検索語ハイライト**: 検索結果内でキーワードが強調表示される

## 📚 API仕様

### GET /books
全書籍の情報を取得

**レスポンス:**
```json
{
  "books": [
    {
      "id": "austen-emma.txt",
      "title": "Emma",
      "author": "Austen",
      "word_count": 158687
    }
  ]
}
```

### GET /search?q={query}
検索クエリに基づいて書籍を検索

**パラメータ:**
- `q`: 検索クエリ（必須）

**レスポンス:**
```json
{
  "query": "love",
  "total_results": 15,
  "results": [
    {
      "id": "austen-emma.txt",
      "title": "Emma",
      "author": "Austen",
      "score": 0.85,
      "snippet": "She was in love with him..."
    }
  ]
}
```

## 🎨 フロントエンド設計

### コンポーネント設計
- **フォルダベース構成**: 各コンポーネントは専用フォルダで管理
- **BEM方式**: CSS クラス命名規則
- **再利用可能性**: プロップベースの柔軟なコンポーネント

### SCSS アーキテクチャ
```scss
// 変数とミックスイン
$primary-color: #3b82f6;
$secondary-color: #64748b;
$border-radius: 0.5rem;

// レスポンシブブレイクポイント
@mixin mobile { @media (max-width: 768px) { @content; } }
@mixin tablet { @media (min-width: 769px) and (max-width: 1024px) { @content; } }
```

### ページ構成
- **/ または /books**: 書籍一覧ページ
- **/search**: 検索ページ

### API設定
- **環境対応**: `config/api.js`で環境に応じた API エンドポイント管理
- **ローカル開発**: `http://localhost:8000` への直接接続
- **Docker環境**: `/api/*` プロキシ経由でアクセス

## 🔧 技術詳細

### TF-IDFベクトル化
- **前処理**: トークン化、ストップワード除去、小文字化
- **特徴量**: 最大5000語、1-2グラム
- **類似度**: コサイン類似度で計算

### スニペット生成
- 検索語を含む文を特定
- 前後25語程度のコンテキストを抽出
- 検索語をハイライト表示

### 検索機能
- リアルタイム検索（デバウンス処理）
- ローディング状態管理
- エラーハンドリング

## 📱 対応ブラウザ

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 🐳 Docker 構成

### アーキテクチャ
- **マルチステージビルド**: フロントエンドの最適化
- **最小限設定**: 不要な設定を除去したシンプルな構成
- **ヘルスチェック**: 自動的なコンテナ健康状態監視
- **プロキシ設定**: nginx による API プロキシとSPAルーティング

### コンテナ仕様
```yaml
# 最小限のdocker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    healthcheck: curl localhost:8000/books
  
  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]
    healthcheck: curl localhost:80/health
```

## 🔮 将来の拡張予定

- **CI/CD**: GitHub Actions パイプライン
- **可観測性**: 
  - Prometheus/Grafana によるメトリクス収集
  - ELK Stack によるログ集約
  - OpenTelemetry による分散トレーシング
- **セキュリティ**: 認証・認可機能
- **パフォーマンス**: Redis キャッシング
- **検索改善**: Elasticsearch 統合

## 🤝 開発ガイドライン

### コードスタイル
- **Python**: Black フォーマッター使用
- **JavaScript/React**: ESLint + Prettier
- **SCSS**: BEM 命名規則

### Git ワークフロー
- feature ブランチでの開発
- プルリクエストによるコードレビュー
- main ブランチへのマージ
