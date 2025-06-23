import './index.scss'

function SearchResult({ result, searchQuery }) {
  const highlightText = (text, query) => {
    if (!query) return text
    
    // 複数の検索語に対応
    const queryWords = query.toLowerCase().split(/\s+/)
    let highlightedText = text
    
    queryWords.forEach(word => {
      if (word.length > 2) { // 短すぎる語はハイライトしない
        const regex = new RegExp(`(${word})`, 'gi')
        highlightedText = highlightedText.replace(regex, '<mark class="highlight">$1</mark>')
      }
    })
    
    return highlightedText
  }

  return (
    <div className="search-result">
      <h3 className="search-result__title">{result.title}</h3>
      <p className="search-result__author">著者: {result.author}</p>
      <div className="search-result__snippet">
        <div 
          className="snippet-text"
          dangerouslySetInnerHTML={{ 
            __html: highlightText(result.snippet, searchQuery) 
          }}
        />
      </div>
      <div className="search-result__score">
        関連度: {(result.score * 100).toFixed(1)}%
      </div>
    </div>
  )
}

export default SearchResult 
