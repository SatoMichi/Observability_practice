import './index.scss'

function ErrorMessage({ error, className = '' }) {
  if (!error) return null

  return (
    <div className={`error-message ${className}`}>
      <div className="error-message__icon">⚠️</div>
      <div className="error-message__content">
        <h3 className="error-message__title">エラーが発生しました</h3>
        <p className="error-message__text">{error}</p>
      </div>
    </div>
  )
}

export default ErrorMessage 
