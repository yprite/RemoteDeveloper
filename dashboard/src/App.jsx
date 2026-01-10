
import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [logs, setLogs] = useState([])
  const [queues, setQueues] = useState({})
  const [status, setStatus] = useState({
    PLAN: 'pending',
    IMPLEMENTATION: 'pending',
    TEST: 'pending'
  })

  const fetchLogs = async () => {
    try {
      const res = await fetch('http://localhost:8001/agent/logs')
      const data = await res.json()
      setLogs(data.logs || [])
      updateStatus(data.logs || [])
    } catch (e) {
      console.error(e)
    }
  }

  const fetchQueues = async () => {
    try {
      const res = await fetch('http://localhost:8001/queues')
      const data = await res.json()
      setQueues(data.queues || {})
    } catch (e) {
      console.error(e)
    }
  }

  const updateStatus = (currentLogs) => {
    const newStatus = { ...status }
    currentLogs.forEach(log => {
      if (log.status) newStatus[log.agent] = log.status
    })
    setStatus(newStatus)
  }

  useEffect(() => {
    // Poll every 1s
    const fetchAll = () => {
      fetchLogs()
      fetchQueues()
    }
    const interval = setInterval(fetchAll, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="container">
      <header>
        <h1>🤖 AI Agent Pipeline</h1>
        <div className="connection-status">
          Connected to Backend
        </div>
      </header>

      <div className="pipeline">
        <Step name="PLAN" status={status.PLAN} />
        <div className="arrow">➔</div>
        <Step name="IMPLEMENTATION" status={status.IMPLEMENTATION} />
        <div className="arrow">➔</div>
        <Step name="TEST" status={status.TEST} />
      </div>

      <div className="queues-section">
        <h2>📥 Queue Status</h2>
        <div className="queues-container">
          {Object.entries(queues).map(([name, items]) => (
            <div key={name} className="queue-card">
              <h3>{name.replace('queue:', '')} <span className="count">{items.length}</span></h3>
              <div className="queue-items">
                {items.length === 0 && <div className="empty-queue">Empty</div>}
                {items.map((item, i) => (
                  <div key={i} className="queue-item">
                    <span className="id">#{item.task?.title || item.meta?.event_id?.slice(-8) || item.context?.chat_id || 'Task'}</span>
                    <span className="task-preview">{(typeof item.task === 'string' ? item.task : item.task?.original_prompt || item.raw || '').substring(0, 50)}...</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="logs-section">
        <h2>📜 Live Execution Logs</h2>
        <div className="logs-window">
          {logs.length === 0 && <div className="empty">Waiting for tasks...</div>}
          {logs.slice().reverse().map((log, i) => (
            <div key={i} className={`log-row ${log.status}`}>
              <div className="meta">
                <span className="time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className="agent">{log.agent}</span>
              </div>
              <div className="msg">{log.message}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Step({ name, status }) {
  const icons = {
    pending: '⏳',
    info: 'ℹ️',
    running: '🌀',
    success: '✅',
    failed: '❌'
  }
  // Fallback to info for unknown
  const icon = icons[status] || icons.info

  return (
    <div className={`step-card ${status}`}>
      <div className="step-icon">{icon}</div>
      <div className="step-name">{name}</div>
      <div className="step-status">{status.toUpperCase()}</div>
    </div>
  )
}

export default App
