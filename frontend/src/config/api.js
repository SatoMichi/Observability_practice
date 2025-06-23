// 環境に応じたAPI_BASE_URLの設定
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.MODE === 'production' 
    ? '/api'  // Docker環境ではnginxのプロキシを使用
    : 'http://localhost:8000'  // ローカル開発環境では直接FastAPIに接続
  )

export { API_BASE_URL } 
