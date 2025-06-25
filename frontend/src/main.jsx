import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.scss'

// OpenTelemetryトレース機能の初期化
import { initializeTracing } from './tracing.js'

// トレースの初期化（アプリケーション起動前）
initializeTracing()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
) 
