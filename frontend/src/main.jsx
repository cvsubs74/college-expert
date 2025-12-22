import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Build version to force cache bust - update this when deploying
const BUILD_VERSION = '2024.12.22.v1';
console.log('[App] Build version:', BUILD_VERSION);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
