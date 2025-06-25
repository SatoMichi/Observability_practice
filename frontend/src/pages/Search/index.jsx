import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorMessage from '../../components/ErrorMessage'
import SearchForm from '../../components/SearchForm'
import SearchResult from '../../components/SearchResult'
import { API_BASE_URL } from '../../config/api'
import { createSpan, getTracer } from '../../tracing.js'
import './index.scss'

function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)

  // シンプルトレーサーの取得
  const tracer = getTracer()

  useEffect(() => {
    const initialQuery = searchParams.get('q')
    if (initialQuery) {
      setQuery(initialQuery)
      performSearch(initialQuery)
    }
  }, [])

  const performSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) return

    // 検索全体をSpanで囲む
    const span = tracer.startSpan('frontend_search', {
      attributes: {
        'search.query': searchQuery,
        'search.page': 'search',
        'user.action': 'search_submit'
      }
    })

    const startTime = Date.now()
    console.log(`[Frontend] 検索開始: "${searchQuery}"`)
    console.log(`[Frontend] API_BASE_URL: "${API_BASE_URL}"`)

    try {
      setLoading(true)
      setError(null)
      setSearchPerformed(true)
      
      // UI更新
      const uiSpan = tracer.startSpan('update_ui_loading', {
        attributes: {
          'ui.component': 'SearchPage',
          'ui.action': 'set_loading_true'
        }
      })
      uiSpan.end()
      
      // API リクエスト準備
      const prepSpan = tracer.startSpan('prepare_api_request', {
        attributes: {
          'api.base_url': API_BASE_URL,
          'search.query': searchQuery
        }
      })
      
      // URLの構築を修正 - 相対パスと絶対パスの両方に対応
      let url
      if (API_BASE_URL.startsWith('http')) {
        // 開発環境: 絶対URL
        url = new URL(`${API_BASE_URL}/search`)
      } else {
        // 本番環境: 相対パス
        url = `${API_BASE_URL}/search?q=${encodeURIComponent(searchQuery)}`
      }
      
      if (API_BASE_URL.startsWith('http')) {
        url.searchParams.append('q', searchQuery)
      }
      
      prepSpan.setAttributes({
        'http.url': url.toString(),
        'http.method': 'GET'
      })
      prepSpan.end()
      
      console.log(`[Frontend] リクエストURL: "${url}"`)
      
      // APIリクエスト実行（Fetchの自動計装でトレースされる）
      const apiSpan = tracer.startSpan('api_request_execute', {
        attributes: {
          'http.url': url.toString(),
          'http.method': 'GET',
          'search.query': searchQuery
        }
      })
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      apiSpan.setAttributes({
        'http.status_code': response.status,
        'http.status_text': response.statusText
      })
      
      // レスポンス処理
      const parseSpan = tracer.startSpan('parse_response', {
        attributes: {
          'response.type': 'json'
        }
      })
      
      const data = await response.json()
      
      parseSpan.setAttributes({
        'search.results_count': data.total_results || 0,
        'search.returned_results': data.results?.length || 0
      })
      parseSpan.end()
      apiSpan.end()
      
      const searchTime = Date.now() - startTime
      console.log(`[Frontend] 検索完了: "${searchQuery}" - ${data.total_results}件の結果 (${searchTime}ms)`)
      
      // 結果処理Span
      const resultsSpan = tracer.startSpan('process_search_results', {
        attributes: {
          'search.results_count': data.total_results || 0,
          'search.processing_time_ms': searchTime
        }
      })
      
      if (data.results.length > 0) {
        const topResult = data.results[0]
        console.log(`[Frontend] 最高スコア: "${topResult.title}" by ${topResult.author} (${topResult.score.toFixed(4)})`)
        
        resultsSpan.setAttributes({
          'search.top_result.title': topResult.title,
          'search.top_result.author': topResult.author,
          'search.top_result.score': topResult.score,
          'search.has_results': true
        })
      } else {
        resultsSpan.setAttributes({
          'search.has_results': false
        })
      }
      
      setResults(data.results)
      
      // URLパラメータを更新
      const urlUpdateSpan = tracer.startSpan('update_url_params', {
        attributes: {
          'url.param.q': searchQuery
        }
      })
      setSearchParams({ q: searchQuery })
      urlUpdateSpan.end()
      
      resultsSpan.end()
      
      // 成功時のSpan属性設定
      span.setAttributes({
        'search.success': true,
        'search.results_count': data.total_results || 0,
        'search.duration_ms': searchTime
      })
      
    } catch (err) {
      const errorTime = Date.now() - startTime
      console.error(`[Frontend] 検索エラー: "${searchQuery}" (${errorTime}ms)`, err)
      
      // エラー処理Span
      const errorSpan = tracer.startSpan('handle_search_error', {
        attributes: {
          'error.type': err.name,
          'error.message': err.message,
          'search.error_time_ms': errorTime
        }
      })
      
      setError('検索に失敗しました')
      setResults([])
      
      // エラー情報をメインSpanに記録
      span.recordException(err)
      span.setAttributes({
        'search.success': false,
        'search.error': err.message,
        'search.duration_ms': errorTime
      })
      
      errorSpan.end()
    } finally {
      // UI更新Span
      const finalUiSpan = tracer.startSpan('update_ui_final', {
        attributes: {
          'ui.component': 'SearchPage',
          'ui.action': 'set_loading_false'
        }
      })
      setLoading(false)
      finalUiSpan.end()
      
      // メインSpanの終了
      span.end()
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
