import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorMessage from '../../components/ErrorMessage'
import SearchForm from '../../components/SearchForm'
import SearchResult from '../../components/SearchResult'
import { API_BASE_URL } from '../../config/api'
import './index.scss'

function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)

  useEffect(() => {
    const initialQuery = searchParams.get('q')
    if (initialQuery) {
      setQuery(initialQuery)
      performSearch(initialQuery)
    }
  }, [])

  const performSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) return

    const startTime = Date.now()
    console.log(`[Frontend] 検索開始: "${searchQuery}"`)

    try {
      setLoading(true)
      setError(null)
      setSearchPerformed(true)
      
      const response = await axios.get(`${API_BASE_URL}/search`, {
        params: { q: searchQuery }
      })
      
      const searchTime = Date.now() - startTime
      console.log(`[Frontend] 検索完了: "${searchQuery}" - ${response.data.total_results}件の結果 (${searchTime}ms)`)
      
      if (response.data.results.length > 0) {
        const topResult = response.data.results[0]
        console.log(`[Frontend] 最高スコア: "${topResult.title}" by ${topResult.author} (${topResult.score.toFixed(4)})`)
      }
      
      setResults(response.data.results)
      
      // URLパラメータを更新
      setSearchParams({ q: searchQuery })
    } catch (err) {
      const errorTime = Date.now() - startTime
      console.error(`[Frontend] 検索エラー: "${searchQuery}" (${errorTime}ms)`, err)
      setError('検索に失敗しました')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-page">
      <SearchForm 
        query={query}
        onQueryChange={setQuery}
        onSubmit={performSearch}
        loading={loading}
      />

      <ErrorMessage error={error} />

      {/* 検索結果 */}
      {searchPerformed && (
        <div className="search-results">
          <div className="results-header">
            <h2>
              検索結果
              {!loading && results.length > 0 && (
                <span className="results-count">
                  ({results.length} 件見つかりました)
                </span>
              )}
            </h2>
          </div>

          {loading && <LoadingSpinner size="md" />}

          {!loading && results.length === 0 && searchPerformed && (
            <div className="no-results">
              <div className="no-results-title">検索結果が見つかりませんでした</div>
              <div className="no-results-subtitle">
                別のキーワードで検索してみてください
              </div>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="results-list">
              {results.map((result, index) => (
                <SearchResult 
                  key={`${result.id}-${index}`}
                  result={result}
                  searchQuery={query}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Search 
