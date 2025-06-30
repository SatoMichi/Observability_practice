import './index.scss'

function SearchForm({ query, onQueryChange, method, onMethodChange, onSubmit, loading }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit()
  }

  return (
    <div className="search-form">
      <h1>📚 Gutenberg Explorer</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="search">
            検索キーワード
          </label>
          <div className="input-group">
            <input
              type="text"
              id="search"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="検索したいキーワードを入力..."
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
            >
              {loading ? '検索中...' : '検索'}
            </button>
          </div>
        </div>
        
        <div className="form-group">
          <label htmlFor="method">
            検索手法
          </label>
          <select
            id="method"
            value={method}
            onChange={(e) => onMethodChange(e.target.value)}
            disabled={loading}
          >
            {/* <option value="tfidf">TF-IDF（従来手法）</option> */}
            {/* <option value="bm25">BM25（高精度）</option> */}
            <option value="slow_tfidf">TF-IDF</option>
          </select>
          <div className="method-description">
            {method === 'tfidf' && (
              <small>🔵 TF-IDF: 単語の出現頻度と希少性を考慮した検索</small>
            )}
            {method === 'bm25' && (
              <small>🟢 BM25: より実用的で高精度な検索アルゴリズム</small>
            )}
            {method === 'slow_tfidf' && (
              <small>🔴 遅いTF-IDF: オブザーバビリティー研修用（意図的に遅い実装）</small>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

export default SearchForm 
