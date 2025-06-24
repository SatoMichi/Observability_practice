import './index.scss'

function SearchForm({ query, onQueryChange, onSubmit, loading }) {
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
      </form>
    </div>
  )
}

export default SearchForm 
