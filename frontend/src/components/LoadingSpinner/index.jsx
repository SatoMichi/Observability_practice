import './index.scss'

function LoadingSpinner({ size = 'md', className = '' }) {
  return (
    <div className={`loading-spinner-container ${className}`}>
      <div className={`loading-spinner loading-spinner--${size}`}></div>
    </div>
  )
}

export default LoadingSpinner 
