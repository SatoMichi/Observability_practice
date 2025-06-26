import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Books from './pages/Books'
import Search from './pages/Search'
import Navbar from './components/Navbar'
import TracingTest from './components/TracingTest'
import './App.scss'

function App() {
  return (
    <Router>
      <div className="app">
        {/* ナビゲーションバー */}
        <Navbar />

        {/* メインコンテンツ */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Search />} />
            <Route path="/books" element={<Books />} />
            <Route path="/search" element={<Search />} />
            <Route path="/tracing-test" element={<TracingTest />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App 
