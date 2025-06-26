# Unleash Feature Flag統合記録

## 概要
バックエンドアプリケーションにUnleash Feature Flag システムを統合する作業記録

## 作業日時
2025年6月26日

## 発生した問題と解決手順

### 1. 初期状態の問題
- バックエンドのコードでUnleashクライアント統合を実装済み
- `docker-compose.yml`にUnleashサービスが含まれていない
- バックエンド起動時に接続エラーが発生

#### エラー内容
```
ConnectionRefusedError: [Errno 111] Connection refused
Unleash Client registration failed due to unexpected HTTP status code.
Unleash Client feature fetch failed due to unexpected HTTP status code.
```

### 2. 解決手順

#### Step 1: Unleashサービスの追加
`docker-compose.yml`に以下のサービスを追加：

1. **PostgreSQLデータベース**（Unleash用）
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=unleash
    - POSTGRES_USER=unleash_user
    - POSTGRES_PASSWORD=unleash_password
    - POSTGRES_HOST_AUTH_METHOD=trust
  ports:
    - "5432:5432"
  volumes:
    - unleash_postgres_data:/var/lib/postgresql/data
```

2. **Unleashサーバー**
```yaml
unleash:
  image: unleashorg/unleash-server:latest
  ports:
    - "4242:4242"
  environment:
    - DATABASE_HOST=postgres
    - DATABASE_NAME=unleash
    - DATABASE_USERNAME=unleash_user
    - DATABASE_PASSWORD=unleash_password
    - DATABASE_SSL=false
    - LOG_LEVEL=info
```

#### Step 2: バックエンド環境変数の設定
```yaml
backend:
  environment:
    - UNLEASH_URL=http://unleash:4242/api
    - UNLEASH_API_TOKEN=default:development.unleash-insecure-client-api-token
  depends_on:
    - unleash
```

#### Step 3: APIトークン認証問題の解決
初期のAPIトークン設定で401 Unauthorizedエラーが継続発生

**試行した方法：**
1. カスタムヘッダー認証: `custom_headers={'Authorization': token}`
2. Bearer認証: `custom_headers={'Authorization': f'Bearer {token}'}`
3. 標準APIトークンパラメータ: `api_token=token`

**最終解決策：**
開発環境用に無認証モードを設定
```yaml
unleash:
  environment:
    - AUTH_TYPE=none
    - UNLEASH_EXPERIMENTAL_FEATURES_DISABLED=false
```

バックエンドクライアント設定を簡素化：
```python
client = UnleashClient(
    url=unleash_url,
    app_name="gutenberg-search-api"
)
```

### 3. 最終的な構成

#### docker-compose.ymlの主要設定
- **Unleashサーバー**: ポート4242で稼働
- **PostgreSQL**: Unleash専用データベース
- **無認証モード**: 開発環境用設定
- **バックエンド**: Unleashサービスに依存

#### 動作確認結果
- ✅ Unleashサーバー正常稼働: `http://localhost:4242`
- ✅ バックエンドAPI正常動作: `http://localhost:8000`
- ✅ Unleashクライアント接続成功
- ✅ 書籍検索API動作確認済み

### 4. 現在のファイル構成

```
backend/
├── main.py              # UnleashClient統合済み
├── requirements.txt     # UnleashClient==5.11.1追加済み
└── ...

docker-compose.yml       # Unleash + PostgreSQL追加済み
notes/
├── unleash.md          # 本ドキュメント
├── logs.md
└── traces.md
```

### 5. Unleash UI アクセス情報

- **URL**: http://localhost:4242
- **デフォルトログイン**:
  - ユーザー名: `admin`
  - パスワード: `unleash4all`

### 6. 今後の開発方針

#### フィーチャーフラグの活用例
1. **検索アルゴリズム切り替え**
   - TF-IDFとBM25の切り替え
   - 新しい検索手法のA/Bテスト

2. **UI機能の段階的展開**
   - 新機能の段階的リリース
   - ユーザーグループ別機能制御

3. **パフォーマンス最適化**
   - 重い処理の制御
   - 負荷分散制御

#### 本番環境への移行時の注意点
1. **認証設定の有効化**
   - `AUTH_TYPE=none`を削除
   - 適切なAPIトークン設定
   - セキュリティヘッダー設定

2. **データベース設定**
   - 永続化ストレージ設定
   - バックアップ戦略
   - パフォーマンスチューニング

3. **モニタリング設定**
   - Unleashメトリクス監視
   - フィーチャーフラグ使用状況追跡

### 7. トラブルシューティング

#### よくある問題
1. **接続エラー**
   - Unleashサービスの起動順序確認
   - ネットワーク設定確認

2. **認証エラー**
   - APIトークン形式確認
   - 環境変数設定確認

3. **データベース接続エラー**
   - PostgreSQL起動状態確認
   - 認証情報確認

#### デバッグコマンド
```bash
# コンテナ状態確認
docker-compose ps

# ログ確認
docker-compose logs unleash
docker-compose logs backend | grep -i unleash

# ヘルスチェック
curl http://localhost:4242/health
curl http://localhost:8000/books
```

### 8. 参考リンク

- [Unleash Documentation](https://docs.getunleash.io/)
- [UnleashClient Python](https://github.com/Unleash/unleash-client-python)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**作業完了**: Unleash Feature Flag システムの統合が正常に完了し、開発環境での動作確認済み。
