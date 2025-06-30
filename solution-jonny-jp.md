# 検索性能最適化変更事項

## 問題点定義

### 1. 意図的な性能ボトルネック
- `slow_tfidf_search`関数がObservability研修用に意図的に遅く実装されている
- 5万回の不要な文字列処理ループ
- 200msの意図的遅延
- 10回の重複ベクトル化処理
- 5回の類似度計算再実行
- スニペット生成時の30ms遅延

### 2. 制限された検索オプション
- フロントエンドで`slow_tfidf`のみ選択可能
- 高速検索方法(`tfidf`, `bm25`)が無効化されている

## 変更事項

### フロントエンド修正
**ファイル**: `frontend/src/components/SearchForm/index.jsx`

```javascript
// 変更前
<option value="slow_tfidf">TF-IDF</option>

// 変更後  
<option value="tfidf">TF-IDF（従来手法）</option>
<option value="bm25">BM25（高精度）</option>
<option value="slow_tfidf">遅いTF-IDF（研修用）</option>
```

### バックエンド修正
**ファイル**: `backend/main.py`

```python
# 変更前: 意図的に遅い実装
def slow_tfidf_search():
    # 5万回の不要なループ
    for i in range(50000):
        temp_string = processed_query.upper().lower().strip()
    time.sleep(0.2)  # 200ms遅延
    
    # 10回の重複ベクトル化
    for i in range(10):
        duplicate_vector = tfidf_vectorizer.transform([processed_query])
        time.sleep(0.05)  # 50ms遅延
    
    # 5回の類似度再計算
    for i in range(5):
        temp_similarities = cosine_similarity(query_vector, tfidf_matrix)
        time.sleep(0.1)  # 100ms遅延

# 変更後: 最適化された実装
def slow_tfidf_search():
    # すべての不要な遅延を除去
    processed_query = preprocess_text(query)
    query_vector = tfidf_vectorizer.transform([processed_query])
    similarities = cosine_similarity(query_vector, tfidf_matrix)
```

## 結果

- 意図的な性能ボトルネックの除去
- すべての検索方法が選択可能
- 高速検索性能の復元 
