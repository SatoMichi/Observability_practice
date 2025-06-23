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

## 🔍 監視とオブザーバビリティ

このプロジェクトは学習目的で作成されており、以下の要素を含んでいます：

### ログ管理
- フロントエンド: ブラウザコンソールログ
- バックエンド: 構造化ログ出力
- 検索クエリ: パフォーマンス計測

### メトリクス
- レスポンス時間計測
- 検索結果件数追跡
- エラー率監視

### 可観測性
- Kubernetes ポッド状態監視
- コンテナリソース使用量
- アプリケーションヘルスチェック

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
