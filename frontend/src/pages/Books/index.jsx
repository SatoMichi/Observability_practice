import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorMessage from '../../components/ErrorMessage'
import BookCard from '../../components/BookCard'
import { API_BASE_URL } from '../../config/api'
import './index.scss'

function Books() {
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBooks()
  }, [])

  const fetchBooks = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_BASE_URL}/books`)
      setBooks(response.data.books)
      setError(null)
    } catch (err) {
      setError('書籍データの取得に失敗しました')
      console.error('Error fetching books:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="books-page">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="books-page">
        <ErrorMessage error={error} />
        <button 
          onClick={fetchBooks}
          className="retry-button"
        >
          再試行
        </button>
      </div>
    )
  }

  return (
    <div className="books-page">
      <div className="page-header">
        <div className="page-header__info">
          <h1>書籍一覧</h1>
          <p>
            Gutenbergコーパスから取得した {books.length} 冊の書籍
          </p>
        </div>
        <div className="page-header__actions">
          <Link
            to="/search"
            className="btn btn--primary"
          >
            検索する
          </Link>
        </div>
      </div>

      <div className="books-grid">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </div>
  )
}

export default Books 
