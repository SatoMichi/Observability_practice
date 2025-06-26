import { Link } from 'react-router-dom'
import './index.scss'

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar__container">
        <div className="navbar__content">
          <div className="navbar__brand">
            <Link to="/">
              📚 Gutenberg Explorer
            </Link>
          </div>
          <div className="navbar__nav">
            <Link to="/books">
              書籍一覧
            </Link>
            <Link to="/search">
              検索
            </Link>
            <Link to="/tracing-test">
              🧪 トレースTest
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar 
