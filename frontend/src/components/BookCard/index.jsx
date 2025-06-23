import { Link } from 'react-router-dom'
import './index.scss'

function BookCard({ book }) {
  return (
    <div className="book-card">
      <div className="book-card__content">
        <div className="book-card__header">
          <div className="book-card__icon">
            <span>📖</span>
          </div>
          <div className="book-card__info">
            <h3>{book.title}</h3>
            <p>{book.author}</p>
          </div>
        </div>
        <div className="book-card__details">
          <div className="word-count">
            語数: {book.word_count.toLocaleString()} 語
          </div>
          <div className="search-link">
            <Link to={`/search?q=${encodeURIComponent(book.title)}`}>
              この本で検索 →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default BookCard 
