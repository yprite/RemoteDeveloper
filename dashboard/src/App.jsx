import { useState, useEffect, useRef } from 'react'
import './App.css'
import config from './config'

// Agent display names mapping
const AGENT_DISPLAY = {
  REQUIREMENT: { short: 'REQ', full: '요구사항 정제', icon: '📋' },
  PLAN: { short: 'PLAN', full: '로드맵/태스크 분해', icon: '🗺️' },
  UXUI: { short: 'UX/UI', full: 'UX/UI 설계', icon: '🎨' },
  ARCHITECT: { short: 'ARCH', full: '아키텍처 설계', icon: '🏗️' },
  CODE: { short: 'CODE', full: '코드 구현', icon: '💻' },
  REFACTORING: { short: 'REF', full: '리팩토링', icon: '♻️' },
  TESTQA: { short: 'TEST', full: '테스트/QA', icon: '🧪' },
  DOC: { short: 'DOC', full: '문서화', icon: '📝' },
  RELEASE: { short: 'REL', full: '배포', icon: '🚀' },
  MONITORING: { short: 'MON', full: '모니터링', icon: '📊' },
}

function App() {
  const [logs, setLogs] = useState([])
  const [queues, setQueues] = useState({})
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [selectedTask, setSelectedTask] = useState(null)
  const [agentStatus, setAgentStatus] = useState({})
  const [isConnected, setIsConnected] = useState(false)
  const [activeTab, setActiveTab] = useState('pipeline') // 'pipeline', 'logs', or 'pending'

  // Pending Actions State
  const [pendingItems, setPendingItems] = useState([])
  const [clarificationResponse, setClarificationResponse] = useState({})

  // Filtering States for Logs
  const [logSearch, setLogSearch] = useState('')
  const [logStatusFilter, setLogStatusFilter] = useState('all') // 'all', 'success', 'failed', 'running'
  const [logAgentFilter, setLogAgentFilter] = useState('all')

  // Sheet Gesture States
  const [isSheetExpanded, setIsSheetExpanded] = useState(false)
  const [dragY, setDragY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const startTouchY = useRef(0)
  const sheetRef = useRef(null)

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/agents`)
      const data = await res.json()
      setAgents(data.agents || [])
      setIsConnected(true)
    } catch (e) {
      console.error(e)
      setIsConnected(false)
    }
  }

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/agent/logs`)
      const data = await res.json()
      setLogs(data.logs || [])
      updateAgentStatus(data.logs || [])
    } catch (e) {
      console.error(e)
    }
  }

  const fetchQueues = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/queues`)
      const data = await res.json()
      setQueues(data.queues || {})
    } catch (e) {
      console.error(e)
    }
  }

  const fetchPending = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/pending`)
      const data = await res.json()
      setPendingItems(data.pending_items || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleClarificationSubmit = async (itemId) => {
    const response = clarificationResponse[itemId]
    if (!response?.trim()) return

    try {
      const res = await fetch(`${config.API_BASE_URL}/pending/${itemId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response })
      })
      if (res.ok) {
        setClarificationResponse(prev => ({ ...prev, [itemId]: '' }))
        fetchPending()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleApproval = async (workItemId, approvalType, approved) => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/workitem/${workItemId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_type: approvalType, approved })
      })
      if (res.ok) {
        fetchPending()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const updateAgentStatus = (currentLogs) => {
    const newStatus = { ...agentStatus }
    currentLogs.forEach(log => {
      if (log.agent && log.status) {
        newStatus[log.agent] = {
          status: log.status,
          message: log.message,
          timestamp: log.timestamp
        }
      }
    })
    setAgentStatus(newStatus)
  }

  const findBottleneck = () => {
    let maxCount = 0
    let bottleneckAgent = null

    Object.entries(queues).forEach(([queueName, queueData]) => {
      if (queueName.startsWith('queue:')) {
        const count = queueData?.count || queueData?.items?.length || 0
        if (count > maxCount) {
          maxCount = count
          bottleneckAgent = queueName.replace('queue:', '')
        }
      }
    })

    return maxCount > 1 ? bottleneckAgent : null
  }

  const getQueueCount = (agentName) => {
    const queueKey = `queue:${agentName}`
    const queueData = queues[queueKey]
    if (!queueData) return 0
    return queueData.count ?? queueData.items?.length ?? 0
  }

  const getQueueItems = (agentName) => {
    const queueKey = `queue:${agentName}`
    const queueData = queues[queueKey]
    return queueData?.items || []
  }

  const getClarificationCount = () => {
    const waiting = queues['waiting:clarification']
    if (!waiting) return 0
    return waiting.count ?? Object.keys(waiting.items || {}).length ?? 0
  }

  useEffect(() => {
    fetchAgents()
    const fetchAll = () => {
      fetchLogs()
      fetchQueues()
      fetchPending()
    }
    fetchAll()
    const interval = setInterval(fetchAll, 1000)
    return () => clearInterval(interval)
  }, [])

  // --- Gesture Handlers ---
  const handleTouchStart = (e) => {
    startTouchY.current = e.touches[0].clientY
    setIsDragging(true)
  }

  const handleTouchMove = (e) => {
    if (!isDragging) return
    const currentY = e.touches[0].clientY
    const delta = currentY - startTouchY.current
    if (delta > 0 || !isSheetExpanded) {
      setDragY(delta)
    }
  }

  const handleTouchEnd = () => {
    setIsDragging(false)
    if (dragY > 150) {
      if (isSheetExpanded) {
        setIsSheetExpanded(false)
        setDragY(0)
      } else {
        closeBottomSheet()
      }
    } else if (dragY < -100 && !isSheetExpanded) {
      setIsSheetExpanded(true)
      setDragY(0)
    } else {
      setDragY(0)
    }
  }

  const handleAgentClick = (agentName) => {
    setSelectedAgent(agentName)
    setSelectedTask(null)
    setIsSheetExpanded(false)
    setDragY(0)
  }

  const handleTaskClick = (task) => {
    setSelectedTask(task)
    setIsSheetExpanded(true)
    setDragY(0)
  }

  const closeBottomSheet = () => {
    setSelectedAgent(null)
    setSelectedTask(null)
    setIsSheetExpanded(false)
    setDragY(0)
  }

  const bottleneckAgent = findBottleneck()
  const clarificationCount = getClarificationCount()

  const filteredLogs = logs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(logSearch.toLowerCase()) ||
      log.agent.toLowerCase().includes(logSearch.toLowerCase())
    const matchesStatus = logStatusFilter === 'all' || log.status === logStatusFilter
    const matchesAgent = logAgentFilter === 'all' || log.agent === logAgentFilter
    return matchesSearch && matchesStatus && matchesAgent
  })

  const sheetStyle = {
    transform: `translateY(${selectedAgent ? (dragY !== 0 ? `${dragY}px` : '0') : '100%'})`,
    transition: isDragging ? 'none' : 'transform 0.4s cubic-bezier(0.32, 0.72, 0, 1)'
  }

  return (
    <div className="container">
      <header>
        <h1>🤖 AI Team</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </div>
      </header>

      <main className="main-scroll-area">
        {activeTab === 'pipeline' ? (
          <div className="pipeline-container">
            {bottleneckAgent && (
              <div className="bottleneck-alert">
                ⚠️ 병목 감지: <strong>{AGENT_DISPLAY[bottleneckAgent]?.full || bottleneckAgent}</strong>
                ({getQueueCount(bottleneckAgent)}개 대기)
              </div>
            )}

            <div className="pipeline-vertical">
              {agents.map((agent, idx) => {
                const isBottleneck = agent.name === bottleneckAgent
                const queueCount = getQueueCount(agent.name)
                const status = agentStatus[agent.name]?.status || 'idle'
                const display = AGENT_DISPLAY[agent.name] || { short: agent.name, full: agent.name, icon: '🔧' }

                return (
                  <div key={agent.name} className="agent-row-wrapper">
                    <div
                      className={`agent-row ${status} ${isBottleneck ? 'bottleneck' : ''}`}
                      onClick={() => handleAgentClick(agent.name)}
                    >
                      <div className="agent-step-number">{idx + 1}</div>
                      <div className="agent-icon">{display.icon}</div>
                      <div className="agent-info">
                        <div className="agent-name">{display.full}</div>
                        <div className="agent-status-text">{status.toUpperCase()}</div>
                      </div>
                      <div className="agent-queue">
                        <span className={`queue-badge ${queueCount > 0 ? 'has-items' : ''} ${isBottleneck ? 'bottleneck' : ''}`}>
                          {queueCount}
                        </span>
                        {agent.name === 'REQUIREMENT' && clarificationCount > 0 && (
                          <span className="clarification-badge">💬 {clarificationCount}</span>
                        )}
                      </div>
                    </div>
                    {idx < agents.length - 1 && <div className="agent-connector">│</div>}
                  </div>
                )
              })}
            </div>
          </div>
        ) : activeTab === 'logs' ? (
          <div className="logs-tab">
            <div className="logs-controls">
              <input
                type="text"
                placeholder="🔍 검색 (로그 내용, 에이전트...)"
                className="log-search-input"
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
              />
              <div className="filter-scroll-row">
                <button
                  className={`filter-badge ${logStatusFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setLogStatusFilter('all')}
                >전체</button>
                <button
                  className={`filter-badge success ${logStatusFilter === 'success' ? 'active' : ''}`}
                  onClick={() => setLogStatusFilter('success')}
                >성공</button>
                <button
                  className={`filter-badge failed ${logStatusFilter === 'failed' ? 'active' : ''}`}
                  onClick={() => setLogStatusFilter('failed')}
                >실패</button>
                <button
                  className={`filter-badge running ${logStatusFilter === 'running' ? 'active' : ''}`}
                  onClick={() => setLogStatusFilter('running')}
                >진행중</button>

                <div className="filter-divider"></div>

                <select
                  className="agent-select-filter"
                  value={logAgentFilter}
                  onChange={(e) => setLogAgentFilter(e.target.value)}
                >
                  <option value="all">모든 에이전트</option>
                  {agents.map(a => (
                    <option key={a.name} value={a.name}>{AGENT_DISPLAY[a.name]?.short || a.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="logs-window">
              {filteredLogs.length === 0 && <div className="empty">조건에 맞는 로그가 없습니다.</div>}
              {filteredLogs.slice().reverse().map((log, i) => (
                <div key={i} className={`log-row ${log.status}`}>
                  <div className="meta">
                    <span className="time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span className="agent">{AGENT_DISPLAY[log.agent]?.short || log.agent}</span>
                  </div>
                  <div className="msg">{log.message}</div>
                </div>
              ))}
            </div>
          </div>
        ) : activeTab === 'pending' ? (
          <div className="pending-tab">
            <div className="pending-header">
              <h2>⏳ 대기 중인 항목</h2>
              <span className="pending-count">{pendingItems.length}개</span>
            </div>

            {pendingItems.length === 0 ? (
              <div className="empty-pending">
                <span className="empty-icon">✅</span>
                <p>처리 대기 중인 항목이 없습니다</p>
              </div>
            ) : (
              <div className="pending-list">
                {pendingItems.map(item => (
                  <div key={item.id} className={`pending-card ${item.type}`}>
                    <div className="pending-card-header">
                      <span className="pending-type-badge">
                        {item.type === 'clarification' ? '💬 정보 요청' : '✅ 승인 필요'}
                      </span>
                      <span className="pending-time">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>

                    {item.type === 'clarification' ? (
                      <div className="clarification-content">
                        <div className="question-box">
                          <strong>질문:</strong> {item.question}
                        </div>
                        {item.original_prompt && (
                          <div className="original-prompt">
                            <strong>원본 요청:</strong> {item.original_prompt.substring(0, 200)}...
                          </div>
                        )}
                        <div className="response-form">
                          <textarea
                            placeholder="추가 정보를 입력하세요..."
                            value={clarificationResponse[item.id] || ''}
                            onChange={(e) => setClarificationResponse(prev => ({
                              ...prev,
                              [item.id]: e.target.value
                            }))}
                          />
                          <button
                            className="submit-btn"
                            onClick={() => handleClarificationSubmit(item.id)}
                          >
                            응답 제출
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="approval-content">
                        <div className="approval-title">{item.title}</div>
                        <div className="approval-state">상태: {item.current_state}</div>

                        {/* Image display for UX/UI approvals */}
                        {item.meta?.images && item.meta.images.length > 0 && (
                          <div className="approval-images">
                            {item.meta.images.map((img, idx) => (
                              <img
                                key={idx}
                                src={img.url || img}
                                alt={img.alt || `Design ${idx + 1}`}
                                className="approval-image"
                                onClick={() => window.open(img.url || img, '_blank')}
                              />
                            ))}
                          </div>
                        )}

                        <div className="approval-buttons">
                          {item.pending_approvals.map(approvalType => (
                            <div key={approvalType} className="approval-action">
                              <span className="approval-label">{approvalType} 승인:</span>
                              <button
                                className="approve-btn"
                                onClick={() => handleApproval(item.id, approvalType, true)}
                              >
                                ✓ 승인
                              </button>
                              <button
                                className="reject-btn"
                                onClick={() => handleApproval(item.id, approvalType, false)}
                              >
                                ✗ 거절
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </main>

      {/* Bottom Navigation Bar */}
      <nav className="bottom-nav">
        <button
          className={`nav-item ${activeTab === 'pipeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('pipeline')}
        >
          <span className="nav-icon">📊</span>
          <span className="nav-label">Pipeline</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <span className="nav-icon">📜</span>
          <span className="nav-label">Logs</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          <span className="nav-icon">⏳</span>
          <span className="nav-label">Pending</span>
          {pendingItems.length > 0 && (
            <span className="pending-nav-badge">{pendingItems.length}</span>
          )}
        </button>
      </nav>

      {/* Backdrop for Bottom Sheet */}
      {selectedAgent && (
        <div
          className="sheet-backdrop"
          onClick={closeBottomSheet}
          style={{
            opacity: Math.max(0, 1 - Math.abs(dragY) / 500),
            pointerEvents: isDragging ? 'none' : 'auto'
          }}
        ></div>
      )}

      {/* Bottom Sheet with Gestures */}
      <div
        ref={sheetRef}
        className={`bottom-sheet ${selectedAgent ? 'open' : ''} ${isSheetExpanded ? 'expanded' : ''}`}
        style={sheetStyle}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="sheet-handle"></div>
        <div className="sheet-header">
          <div className="sheet-title">
            <span className="agent-icon">{AGENT_DISPLAY[selectedAgent]?.icon}</span>
            <h3>{AGENT_DISPLAY[selectedAgent]?.full || selectedAgent}</h3>
          </div>
          <button className="close-btn" onClick={closeBottomSheet}>✕</button>
        </div>
        <div className="sheet-content">
          {!selectedTask ? (
            <div className="queue-list-section">
              <div className="section-header">
                <h4>📥 대기 목록 ({getQueueCount(selectedAgent)})</h4>
              </div>
              <div className="queue-list">
                {getQueueItems(selectedAgent).map((item, idx) => (
                  <div key={idx} className="queue-item-card" onClick={() => handleTaskClick(item)}>
                    <div className="task-header">
                      <span className="task-id">#{item.meta?.event_id?.slice(-8)}</span>
                      <span className="task-time">{new Date(item.meta?.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="task-preview">{item.task?.original_prompt?.substring(0, 60)}...</div>
                  </div>
                ))}
                {getQueueItems(selectedAgent).length === 0 && (
                  <div className="empty-state">대기 중인 작업이 없습니다.</div>
                )}
              </div>
            </div>
          ) : (
            <div className="task-detail-section">
              <button className="back-btn" onClick={() => setSelectedTask(null)}>← 리스트로 돌아가기</button>
              <div className="detail-grid">
                <div className="detail-item full">
                  <label>Original Prompt</label>
                  <div className="detail-value prompt-text">{selectedTask.task?.original_prompt}</div>
                </div>
                <div className="detail-item full">
                  <label>Context</label>
                  <pre className="context-json">{JSON.stringify(selectedTask.context, null, 2)}</pre>
                </div>
                <div className="history-timeline">
                  {selectedTask.history?.map((h, i) => (
                    <div key={i} className="history-step">
                      <span className="step-point"></span>
                      <span className="step-stage">{h.stage}</span>
                      <span className="step-msg">{h.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
