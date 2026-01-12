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
  EVALUATION: { short: 'EVAL', full: '작업 평가', icon: '📈' },
}

function App() {
  const [logs, setLogs] = useState([])
  const [queues, setQueues] = useState({})
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [selectedTask, setSelectedTask] = useState(null)
  const [agentStatus, setAgentStatus] = useState({})
  const [isConnected, setIsConnected] = useState(false)
  const [activeTab, setActiveTab] = useState('pipeline') // 'pipeline', 'logs', 'pending', 'stats', 'tasks', or 'settings'
  const [expandedResults, setExpandedResults] = useState({}) // Track expanded agent results

  // Tasks History State
  const [tasks, setTasks] = useState([])
  const [selectedHistoryTask, setSelectedHistoryTask] = useState(null)

  // Stats State
  const [agentMetrics, setAgentMetrics] = useState({})
  const [improvements, setImprovements] = useState([])

  // Settings State
  const [llmSettings, setLlmSettings] = useState({})
  const [availableAdapters, setAvailableAdapters] = useState([])
  const [systemStatus, setSystemStatus] = useState({ backend: 'unknown', n8n: 'unknown' })
  const [repos, setRepos] = useState([])
  const [newRepoUrl, setNewRepoUrl] = useState('')

  // Pending Actions State
  const [pendingItems, setPendingItems] = useState([])
  const [clarificationResponse, setClarificationResponse] = useState({})
  const [clarificationImages, setClarificationImages] = useState({}) // {itemId: [base64Images]}
  const [expandedDataItems, setExpandedDataItems] = useState({}) // {itemId-key: true/false}

  // Filtering States for Logs
  const [logSearch, setLogSearch] = useState('')
  const [logStatusFilter, setLogStatusFilter] = useState('all') // 'all', 'success', 'failed', 'running'
  const [logAgentFilter, setLogAgentFilter] = useState('all')

  // Sheet Gesture States
  const [isSheetExpanded, setIsSheetExpanded] = useState(false)
  const [dragY, setDragY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)

  const [sheetTab, setSheetTab] = useState('queue') // 'queue' or 'history'
  const [logSubTab, setLogSubTab] = useState('system') // 'system' or 'tasks'
  const [agentHistory, setAgentHistory] = useState([])
  const [selectedHistoryItem, setSelectedHistoryItem] = useState(null) // For history item detail view
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
    } catch (e) {
      console.error(e)
    }
  }

  const fetchAgentStatus = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/agents/status`)
      const data = await res.json()
      setAgentStatus(data.statuses || {})
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

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/metrics/agents`)
      const data = await res.json()
      setAgentMetrics(data.agents || {})

      const impRes = await fetch(`${config.API_BASE_URL}/metrics/improvements`)
      const impData = await impRes.json()
      setImprovements(impData.improvements || [])
    } catch (e) {
      console.error(e)
    }
  }

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/settings/llm`)
      const data = await res.json()
      setLlmSettings(data.settings || {})

      const adRes = await fetch(`${config.API_BASE_URL}/settings/llm/adapters`)
      const adData = await adRes.json()
      setAvailableAdapters(adData.adapters || [])

      fetchSystemStatus()
    } catch (e) {
      console.error(e)
    }
  }

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/tasks?limit=50`)
      const data = await res.json()
      setTasks(data.tasks || [])
    } catch (e) {
      console.error(e)
    }
  }

  const clearLogs = (e) => {
    if (e && e.stopPropagation) {
      e.stopPropagation()
      e.preventDefault()
    }
    // Clear only the client-side displayed logs
    setLogs([])
  }

  const fetchTaskDetail = async (taskId) => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/tasks/${taskId}`)
      const data = await res.json()
      setSelectedHistoryTask(data)
    } catch (e) {
      console.error(e)
    }
  }

  const fetchSystemStatus = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/system/status`)
      const data = await res.json()
      setSystemStatus(data)
    } catch (e) {
      console.error(e)
    }
  }

  const saveLlmSettings = async () => {
    try {
      await fetch(`${config.API_BASE_URL}/settings/llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: llmSettings })
      })
    } catch (e) {
      console.error(e)
    }
  }

  const handleLlmChange = (agent, value) => {
    setLlmSettings(prev => ({ ...prev, [agent]: value }))
  }

  const handleClarificationSubmit = async (itemId) => {
    const response = clarificationResponse[itemId]
    const images = clarificationImages[itemId] || []

    // Need either text or images
    if (!response?.trim() && images.length === 0) return

    try {
      let imageUrls = []

      // Upload images first if any
      if (images.length > 0) {
        const uploadRes = await fetch(`${config.API_BASE_URL}/files/upload-images`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ images })
        })
        if (uploadRes.ok) {
          const uploadData = await uploadRes.json()
          imageUrls = uploadData.urls || []
        }
      }

      // Submit response with images
      const res = await fetch(`${config.API_BASE_URL}/pending/${itemId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          response: response || '',
          images: imageUrls.length > 0 ? imageUrls : null
        })
      })
      if (res.ok) {
        setClarificationResponse(prev => ({ ...prev, [itemId]: '' }))
        setClarificationImages(prev => ({ ...prev, [itemId]: [] }))
        fetchPending()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleImageUpload = (itemId, e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return

    files.forEach(file => {
      const reader = new FileReader()
      reader.onload = (event) => {
        setClarificationImages(prev => ({
          ...prev,
          [itemId]: [...(prev[itemId] || []), event.target.result]
        }))
      }
      reader.readAsDataURL(file)
    })

    // Reset input
    e.target.value = ''
  }

  const removeImage = (itemId, index) => {
    setClarificationImages(prev => ({
      ...prev,
      [itemId]: (prev[itemId] || []).filter((_, i) => i !== index)
    }))
  }

  const handleApproval = async (itemId, approvalType, approved, itemType = 'approval', source = 'workitem') => {
    try {
      let res
      if (itemType === 'debug') {
        // Debug mode approval uses different endpoint
        res = await fetch(`${config.API_BASE_URL}/pending/${itemId}/debug-approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved })
        })
      } else if (source === 'event') {
        // Event-based approval from agent pipeline
        res = await fetch(`${config.API_BASE_URL}/pending/${itemId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved, approval_type: approvalType })
        })
      } else {
        // WorkItem-based approval (orchestrator workflow)
        res = await fetch(`${config.API_BASE_URL}/workitem/${itemId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approval_type: approvalType, approved })
        })
      }
      if (res.ok) {
        fetchPending()
      } else {
        const errData = await res.json().catch(() => ({}))
        console.error('Approval failed:', errData.detail || res.statusText)
      }
    } catch (e) {
      console.error(e)
    }
  }

  // Agent status is now fetched from Redis via /agents/status endpoint

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

  // Get pending items count for a specific agent
  const getAgentPendingCount = (agentName) => {
    return pendingItems.filter(item =>
      item.current_state === agentName ||
      item.agent === agentName
    ).length
  }

  // Get pending items for a specific agent
  const getAgentPendingItems = (agentName) => {
    return pendingItems.filter(item =>
      item.current_state === agentName ||
      item.agent === agentName
    )
  }

  const fetchRepos = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/settings/repos`)
      const data = await res.json()
      setRepos(data.repositories || [])
    } catch (e) {
      console.error(e)
    }
  }

  const addRepo = async () => {
    if (!newRepoUrl) return
    try {
      const res = await fetch(`${config.API_BASE_URL}/settings/repos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newRepoUrl })
      })
      if (res.ok) {
        setNewRepoUrl('')
        fetchRepos()
        alert('저장소가 추가되었습니다. 인덱싱이 시작됩니다.')
      }
    } catch (e) {
      alert('저장소 추가 실패: ' + e.message)
    }
  }

  const deleteRepo = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return
    try {
      await fetch(`${config.API_BASE_URL}/settings/repos/${id}`, { method: 'DELETE' })
      fetchRepos()
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchAgents()
    fetchSettings()
    fetchRepos()  // Fetch repos
    const fetchAll = () => {
      fetchLogs()
      fetchQueues()
      fetchPending()
      fetchMetrics()
      fetchAgentStatus()
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

  const handleAgentClick = async (agentName) => {
    setSelectedAgent(agentName)
    setSelectedTask(null)
    setSelectedHistoryItem(null)
    setIsSheetExpanded(false)
    setDragY(0)
    setSheetTab('queue')
    // Fetch agent history
    try {
      const res = await fetch(`${config.API_BASE_URL}/agent/${agentName}/history?limit=20`)
      const data = await res.json()
      setAgentHistory(data.history || [])
    } catch (e) {
      console.error(e)
      setAgentHistory([])
    }
  }

  const handleTaskClick = (task) => {
    setSelectedTask(task)
    setIsSheetExpanded(true)
    setDragY(0)
  }

  const closeBottomSheet = () => {
    setSelectedAgent(null)
    setSelectedTask(null)
    setSelectedHistoryItem(null)
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
            {/* Total pending approvals alert */}
            {(() => {
              const totalPending = agents.reduce((sum, agent) => sum + getAgentPendingCount(agent.name), 0)
              return totalPending > 0 ? (
                <div className="approval-alert">
                  🔔 <strong>승인 대기: {totalPending}건</strong>
                  <span className="approval-hint">에이전트를 클릭하여 승인하세요</span>
                </div>
              ) : null
            })()}

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
                const pendingCount = getAgentPendingCount(agent.name)
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
                        {pendingCount > 0 && (
                          <span className="pending-badge">⏳ {pendingCount}</span>
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
            <div className="sheet-tabs" style={{ padding: '10px 10px 0' }}>
              <button
                className={`sheet-tab ${logSubTab === 'system' ? 'active' : ''}`}
                onClick={() => setLogSubTab('system')}
              >📜 시스템 로그</button>
              <button
                className={`sheet-tab ${logSubTab === 'tasks' ? 'active' : ''}`}
                onClick={() => { setLogSubTab('tasks'); fetchTasks(); }}
              >📋 작업 이력</button>
            </div>

            {logSubTab === 'system' ? (
              <>
                <div className="logs-controls">
                  <div className="logs-actions">
                    <button type="button" className="clear-logs-btn" onClick={(e) => clearLogs(e)}>🗑️ 로그 비우기</button>
                  </div>
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
                    <button
                      className={`filter-badge cancelled ${logStatusFilter === 'cancelled' ? 'active' : ''}`}
                      onClick={() => setLogStatusFilter('cancelled')}
                    >취소</button>

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
              </>
            ) : (
              <div className="tasks-tab">
                {!selectedHistoryTask ? (
                  <>
                    <div className="tasks-header">
                      <h2>작업 이력 ({tasks.length})</h2>
                      <button className="refresh-btn" onClick={fetchTasks}>🔄</button>
                    </div>
                    <div className="tasks-list">
                      {tasks.map(task => (
                        <div
                          key={task.id || task.task_id}
                          className={`task-card ${task.status === 'COMPLETED' ? 'completed' : task.status === 'FAILED' ? 'failed' : 'pending'}`}
                          onClick={() => fetchTaskDetail(task.id || task.task_id)}
                        >
                          <div className="task-card-header">
                            <span className="task-id">#{(task.id || task.task_id)?.slice(0, 8)}</span>
                            <span className={`task-status-badge ${task.status}`}>{task.status}</span>
                          </div>
                          <div className="task-card-prompt">
                            {task.original_prompt}
                          </div>
                          <div className="task-card-meta">
                            Created: {new Date(task.created_at).toLocaleString()}
                          </div>
                        </div>
                      ))}
                      {tasks.length === 0 && <div className="empty-state">기록된 작업이 없습니다.</div>}
                    </div>
                  </>
                ) : (
                  <div className="task-detail">
                    <button className="back-btn" onClick={() => setSelectedHistoryTask(null)}>← 목록으로</button>
                    <div className="task-detail-header">
                      <h3>#{(selectedHistoryTask.task_id || selectedHistoryTask.id)?.slice(-8)}</h3>
                      <span className={`task-status ${selectedHistoryTask.status?.toLowerCase()}`}>
                        {selectedHistoryTask.status}
                      </span>
                    </div>
                    <div className="task-detail-prompt">
                      <label>원본 요청</label>
                      <p>{selectedHistoryTask.original_prompt}</p>
                    </div>
                    <div className="task-timeline">
                      <h4>📍 에이전트 시퀀스</h4>
                      {selectedHistoryTask.events?.map((evt, idx) => (
                        <div key={idx} className={`timeline-item ${evt.status}`}>
                          <div className="timeline-dot"></div>
                          <div className="timeline-content">
                            <div className="timeline-header">
                              <span className="timeline-agent">{AGENT_DISPLAY[evt.agent]?.icon} {evt.agent}</span>
                              <span className={`timeline-status ${evt.status}`}>{evt.status}</span>
                            </div>
                            {evt.message && <div className="timeline-message">{evt.message}</div>}
                            <div className="timeline-time">{new Date(evt.created_at).toLocaleTimeString()}</div>
                          </div>
                        </div>
                      ))}
                      {(!selectedHistoryTask.events || selectedHistoryTask.events.length === 0) && (
                        <div className="empty-state">에이전트 이벤트가 없습니다.</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : activeTab === 'stats' ? (
          <div className="stats-tab">
            <div className="stats-header">
              <h2>📈 에이전트 통계</h2>
            </div>
            <div className="stats-grid">
              {Object.entries(agentMetrics).map(([agent, stats]) => (
                <div key={agent} className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-icon">{AGENT_DISPLAY[agent]?.icon || '🔧'}</span>
                    <span className="stat-name">{AGENT_DISPLAY[agent]?.full || agent}</span>
                  </div>
                  <div className="stat-body">
                    <div className="stat-row">
                      <span>총 작업</span>
                      <strong>{stats.total || 0}</strong>
                    </div>
                    <div className="stat-row">
                      <span>성공률</span>
                      <strong className={stats.success_rate >= 70 ? 'good' : 'bad'}>
                        {stats.success_rate || 0}%
                      </strong>
                    </div>
                    <div className="stat-row">
                      <span>평균 소요</span>
                      <strong>{stats.avg_duration_ms || 0}ms</strong>
                    </div>
                  </div>
                  <div className="stat-bar">
                    <div
                      className="stat-bar-fill"
                      style={{ width: `${stats.success_rate || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {Object.keys(agentMetrics).length === 0 && (
              <div className="empty-stats">아직 통계 데이터가 없습니다. 파이프라인을 실행해보세요.</div>
            )}
            {improvements.length > 0 && (
              <div className="improvements-section">
                <h3>💡 개선점 제안</h3>
                <ul className="improvements-list">
                  {improvements.map((imp, idx) => (
                    <li key={idx}>{imp}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : activeTab === 'settings' ? (
          <div className="settings-tab">
            <h2 className="settings-title">⚙️ 설정</h2>

            {/* Debug Mode Toggle */}
            <div className="setting-row toggle-row">
              <div className="setting-row-info">
                <span className="setting-row-icon">🐛</span>
                <span className="setting-row-label">디버깅 모드</span>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={systemStatus.debugMode || false}
                  onChange={async (e) => {
                    await fetch(`${config.API_BASE_URL}/settings/debug`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ enabled: e.target.checked })
                    })
                    fetchSystemStatus()
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            {/* LLM Settings Section */}
            <div
              className="setting-row expandable"
              onClick={() => setActiveTab('settings:llm')}
            >
              <div className="setting-row-info">
                <span className="setting-row-icon">🤖</span>
                <span className="setting-row-label">LLM 설정</span>
              </div>
              <span className="chevron">›</span>
            </div>

            {/* Service Control Section */}
            <div
              className="setting-row expandable"
              onClick={() => setActiveTab('settings:services')}
            >
              <div className="setting-row-info">
                <span className="setting-row-icon">🖥️</span>
                <span className="setting-row-label">서비스 제어</span>
              </div>
              <span className="chevron">›</span>
            </div>

            {/* Repository Settings Section */}
            <div
              className="setting-row expandable"
              onClick={() => setActiveTab('settings:repos')}
            >
              <div className="setting-row-info">
                <span className="setting-row-icon">📂</span>
                <span className="setting-row-label">Git 저장소 (RAG)</span>
              </div>
              <span className="chevron">›</span>
            </div>
          </div>
        ) : activeTab === 'settings:llm' ? (
          <div className="settings-tab">
            <div className="settings-header">
              <button className="back-btn" onClick={() => setActiveTab('settings')}>← 설정</button>
              <button className="save-btn" onClick={saveLlmSettings}>저장</button>
            </div>
            <h3>🤖 LLM 설정</h3>
            <p className="settings-desc">각 에이전트가 사용할 LLM 백엔드를 선택하세요.</p>
            <div className="settings-grid">
              {Object.entries(llmSettings).map(([agent, adapter]) => (
                <div key={agent} className="setting-card">
                  <div className="setting-card-header">
                    <span className="setting-icon">{AGENT_DISPLAY[agent]?.icon || '🔧'}</span>
                    <span className="setting-name">{AGENT_DISPLAY[agent]?.full || agent}</span>
                  </div>
                  <select
                    className="llm-select"
                    value={adapter}
                    onChange={(e) => handleLlmChange(agent, e.target.value)}
                  >
                    {availableAdapters.map(ad => (
                      <option key={ad.name} value={ad.name}>{ad.label}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        ) : activeTab === 'settings:services' ? (
          <div className="settings-tab">
            <div className="settings-header">
              <button className="back-btn" onClick={() => setActiveTab('settings')}>← 설정</button>
            </div>
            <h3>🖥️ 서비스 제어</h3>
            <div className="service-controls">
              <div className="service-card">
                <div className="service-info">
                  <span className="service-name">Backend</span>
                  <span className={`service-status ${systemStatus.backend}`}>
                    {systemStatus.backend === 'running' ? '✅ Running' : '⚠️ Unknown'}
                  </span>
                </div>
                <button className="service-btn restart" onClick={async () => {
                  if (confirm('Backend를 재시작하시겠습니까?')) {
                    await fetch(`${config.API_BASE_URL}/system/restart`, { method: 'POST' })
                  }
                }}>🔄 Restart</button>
              </div>
              <div className="service-card">
                <div className="service-info">
                  <span className="service-name">n8n Workflow</span>
                  <span className={`service-status ${systemStatus.n8n}`}>
                    {systemStatus.n8n === 'running' ? '✅ Running' : '❌ Stopped'}
                  </span>
                </div>
                <div className="service-btns">
                  <button className="service-btn start" onClick={async () => {
                    await fetch(`${config.API_BASE_URL}/system/n8n/start`, { method: 'POST' })
                    setTimeout(() => fetchSystemStatus(), 2000)
                  }}>▶️</button>
                  <button className="service-btn stop" onClick={async () => {
                    await fetch(`${config.API_BASE_URL}/system/n8n/stop`, { method: 'POST' })
                    setTimeout(() => fetchSystemStatus(), 1000)
                  }}>⏹️</button>
                  <button className="service-btn restart" onClick={async () => {
                    await fetch(`${config.API_BASE_URL}/system/n8n/restart`, { method: 'POST' })
                    setTimeout(() => fetchSystemStatus(), 2000)
                  }}>🔄</button>
                </div>
              </div>
              <div className="service-card">
                <div className="service-info">
                  <span className="service-name">Redis</span>
                  <span className={`service-status ${systemStatus.redis || 'unknown'}`}>
                    {systemStatus.redis === 'running' ? '✅ Running' : '⚠️ Unknown'}
                  </span>
                </div>
                <span className="service-note">start_system.py로 관리</span>
              </div>
            </div>
          </div>
        ) : activeTab === 'settings:repos' ? (
          <div className="settings-tab">
            <div className="settings-header">
              <button className="back-btn" onClick={() => setActiveTab('settings')}>← 설정</button>
            </div>
            <h3>📂 Git 저장소 관리</h3>
            <p className="settings-desc">RAG 시스템이 학습할 Git 저장소를 관리합니다.</p>

            <div className="repo-input-group">
              <input
                type="text"
                className="repo-input"
                placeholder="https://github.com/username/repo"
                value={newRepoUrl}
                onChange={(e) => setNewRepoUrl(e.target.value)}
              />
              <button className="repo-add-btn" onClick={addRepo}>추가</button>
            </div>

            <div className="repo-list">
              {repos.length === 0 ? (
                <div className="empty-state">등록된 저장소가 없습니다.</div>
              ) : (
                repos.map(repo => (
                  <div key={repo.id} className="repo-card">
                    <div className="repo-info">
                      <span className="repo-url">{repo.url}</span>
                      <span className="repo-status">
                        {repo.last_indexed_at
                          ? `Last indexed: ${new Date(repo.last_indexed_at).toLocaleString()}`
                          : 'Not indexed yet'}
                      </span>
                    </div>
                    <button className="repo-delete-btn" onClick={() => deleteRepo(repo.id)}>삭제</button>
                  </div>
                ))
              )}
            </div>
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
          {pendingItems.length > 0 && (
            <span className="pending-nav-badge">{pendingItems.length}</span>
          )}
        </button>
        <button
          className={`nav-item ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <span className="nav-icon">📜</span>
          <span className="nav-label">Logs</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          <span className="nav-icon">📈</span>
          <span className="nav-label">Stats</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <span className="nav-icon">⚙️</span>
          <span className="nav-label">Settings</span>
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
          {!selectedTask && !selectedHistoryItem ? (
            <div className="queue-list-section">
              <div className="sheet-tabs">
                <button
                  className={`sheet-tab ${sheetTab === 'queue' ? 'active' : ''}`}
                  onClick={() => setSheetTab('queue')}
                >📥 대기 ({getQueueCount(selectedAgent) + getAgentPendingCount(selectedAgent)})</button>
                <button
                  className={`sheet-tab ${sheetTab === 'history' ? 'active' : ''}`}
                  onClick={() => setSheetTab('history')}
                >📜 처리기록</button>
              </div>

              {sheetTab === 'queue' ? (
                <div className="queue-list">
                  {/* Pending items requiring approval */}
                  {getAgentPendingItems(selectedAgent).map((item, idx) => (
                    <div key={`pending-${idx}`} className={`queue-item-card pending-item ${item.type}`}>
                      <div className="task-header">
                        <span className={`pending-type-badge ${item.type}`}>
                          {item.type === 'clarification' ? '💬 정보 요청' :
                            item.type === 'debug' ? '🐛 디버그' : '⏳ 승인 필요'}
                        </span>
                        <span className="task-time">{new Date(item.created_at).toLocaleTimeString()}</span>
                      </div>

                      {/* Different display for clarification vs other types */}
                      {item.type === 'clarification' ? (
                        <>
                          <div className="clarification-original">
                            <span className="label">원본 요청:</span> {item.original_prompt?.substring(0, 100)}...
                          </div>
                          <div className="clarification-question-box">
                            <span className="question-icon">❓</span>
                            <span className="question-text">{item.question}</span>
                          </div>
                          <div className="inline-clarification">
                            <textarea
                              placeholder="추가 정보를 입력하세요..."
                              value={clarificationResponse[item.id] || ''}
                              onChange={(e) => setClarificationResponse(prev => ({
                                ...prev,
                                [item.id]: e.target.value
                              }))}
                              onClick={(e) => e.stopPropagation()}
                            />

                            {/* Image upload section */}
                            <div className="image-upload-section">
                              <label className="image-upload-btn" onClick={(e) => e.stopPropagation()}>
                                📷 이미지 첨부
                                <input
                                  type="file"
                                  accept="image/*"
                                  multiple
                                  onChange={(e) => handleImageUpload(item.id, e)}
                                  style={{ display: 'none' }}
                                />
                              </label>

                              {/* Image previews */}
                              {(clarificationImages[item.id] || []).length > 0 && (
                                <div className="image-previews">
                                  {clarificationImages[item.id].map((img, imgIdx) => (
                                    <div key={imgIdx} className="image-preview-item">
                                      <img src={img} alt={`Preview ${imgIdx + 1}`} />
                                      <button
                                        className="remove-image-btn"
                                        onClick={(e) => { e.stopPropagation(); removeImage(item.id, imgIdx); }}
                                      >×</button>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>

                            <button
                              className="approve-btn submit-response-btn"
                              onClick={(e) => { e.stopPropagation(); handleClarificationSubmit(item.id); }}
                            >
                              ✓ 응답 제출 {(clarificationImages[item.id] || []).length > 0 && `(+${clarificationImages[item.id].length} 이미지)`}
                            </button>
                          </div>
                        </>
                      ) : item.type === 'debug' ? (
                        <>
                          {/* Debug item detailed view */}
                          <div className="debug-info-section">
                            <div className="debug-agent-badge">
                              <span className="agent-icon">{AGENT_DISPLAY[item.agent]?.icon || '🔧'}</span>
                              <span className="agent-name">{AGENT_DISPLAY[item.agent]?.full || item.agent}</span>
                            </div>

                            <div className="debug-original-prompt">
                              <span className="label">📝 원본 요청:</span>
                              <p>{item.original_prompt}</p>
                            </div>

                            {/* Previous agent results */}
                            {item.data && Object.keys(item.data).length > 0 && (
                              <div className="debug-previous-data">
                                <span className="label">📊 이전 에이전트 결과:</span>
                                <div className="previous-data-list">
                                  {Object.entries(item.data).map(([key, value]) => {
                                    const expandKey = `${item.id}-${key}`;
                                    const isExpanded = expandedDataItems[expandKey];
                                    const valueStr = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
                                    const isLong = valueStr.length > 200;

                                    return (
                                      <div key={key} className="previous-data-item">
                                        <div className="data-key-row">
                                          <span className="data-key">{key}:</span>
                                          {isLong && (
                                            <button
                                              className="more-btn"
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setExpandedDataItems(prev => ({
                                                  ...prev,
                                                  [expandKey]: !prev[expandKey]
                                                }));
                                              }}
                                            >
                                              {isExpanded ? '접기 ▲' : '더보기 ▼'}
                                            </button>
                                          )}
                                        </div>
                                        <pre className={`data-value ${isExpanded ? 'expanded' : ''}`}>
                                          {isExpanded ? valueStr : (isLong ? valueStr.substring(0, 200) + '...' : valueStr)}
                                        </pre>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Processing history */}
                            {item.history && item.history.length > 0 && (
                              <div className="debug-history">
                                <span className="label">📍 처리 이력:</span>
                                <div className="history-steps">
                                  {item.history.slice(-5).map((h, idx) => (
                                    <div key={idx} className="history-step-mini">
                                      <span className="step-stage">{h.stage}</span>
                                      <span className="step-msg">{h.message?.substring(0, 50)}...</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>

                          <div className="debug-action-buttons">
                            <button
                              className="approve-btn debug-run-btn"
                              onClick={(e) => { e.stopPropagation(); handleApproval(item.id, item.agent, true, 'debug'); }}
                            >
                              ▶️ {AGENT_DISPLAY[item.agent]?.full || item.agent} 실행
                            </button>
                            <button
                              className="reject-btn debug-cancel-btn"
                              onClick={(e) => { e.stopPropagation(); handleApproval(item.id, item.agent, false, 'debug'); }}
                            >
                              ❌ 취소
                            </button>
                          </div>
                        </>
                      ) : (
                        <div className="task-preview">{item.title || item.message || item.original_prompt?.substring(0, 60)}</div>
                      )}

                      {/* Approval buttons for approval types only */}
                      {item.type === 'approval' && (
                        <div className="inline-approval-buttons">
                          {(item.pending_approvals || []).map(approvalType => (
                            <div key={approvalType} className="approval-btn-group">
                              <button
                                className="approve-btn"
                                onClick={(e) => { e.stopPropagation(); handleApproval(item.id, approvalType, true, 'approval', item.source); }}
                              >
                                ✓ {approvalType} 승인
                              </button>
                              <button
                                className="reject-btn"
                                onClick={(e) => { e.stopPropagation(); handleApproval(item.id, approvalType, false, 'approval', item.source); }}
                              >
                                ✗ 거절
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Queue items (processing) */}
                  {getQueueItems(selectedAgent).map((item, idx) => (
                    <div key={`queue-${idx}`} className="queue-item-card" onClick={() => handleTaskClick(item)}>
                      <div className="task-header">
                        <span className="task-id">#{item.meta?.event_id?.slice(-8)}</span>
                        <span className="task-time">{new Date(item.meta?.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <div className="task-preview">{item.task?.original_prompt?.substring(0, 60)}...</div>
                    </div>
                  ))}

                  {getQueueItems(selectedAgent).length === 0 && getAgentPendingItems(selectedAgent).length === 0 && (
                    <div className="empty-state">대기 중인 작업이 없습니다.</div>
                  )}
                </div>
              ) : (
                <div className="history-list">
                  {/* Filter to show only final state per task_id */}
                  {(() => {
                    const seen = new Set()
                    return agentHistory.filter(item => {
                      if (!item.task_id) return true
                      if (seen.has(item.task_id)) return false
                      seen.add(item.task_id)
                      return true
                    }).map((item, idx) => (
                      <div
                        key={idx}
                        className={`history-item-card ${item.status}`}
                        onClick={() => setSelectedHistoryItem(item)}
                      >
                        <div className="task-header">
                          <span className="task-id">#{item.task_id?.slice(-8)}</span>
                          <span className={`status-badge ${item.status}`}>{item.status}</span>
                        </div>
                        <div className="task-preview">{item.original_prompt?.substring(0, 50) || item.message}</div>
                        <div className="task-time">{new Date(item.created_at).toLocaleString()}</div>
                      </div>
                    ))
                  })()}
                  {agentHistory.length === 0 && (
                    <div className="empty-state">처리된 기록이 없습니다.</div>
                  )}
                </div>
              )}
            </div>
          ) : selectedHistoryItem ? (
            <div className="history-detail-section">
              <button className="back-btn" onClick={() => setSelectedHistoryItem(null)}>← 목록으로</button>
              <div className="detail-grid">
                <div className="detail-item full">
                  <label>📋 원본 요청</label>
                  <div className="detail-value prompt-text">{selectedHistoryItem.original_prompt}</div>
                </div>

                <div className="detail-item">
                  <label>🏷️ 상태</label>
                  <span className={`status-badge large ${selectedHistoryItem.status}`}>{selectedHistoryItem.status}</span>
                </div>

                <div className="detail-item">
                  <label>🕐 처리 시간</label>
                  <div className="detail-value">{new Date(selectedHistoryItem.created_at).toLocaleString()}</div>
                </div>

                {selectedHistoryItem.message && (
                  <div className="detail-item full">
                    <label>💬 처리 결과</label>
                    <div className="detail-value">{selectedHistoryItem.message}</div>
                  </div>
                )}

                {selectedHistoryItem.result && (
                  <div className="detail-item full">
                    <label>📤 다음 에이전트에 전달된 정보</label>
                    <pre className="context-json">{JSON.stringify(selectedHistoryItem.result, null, 2)}</pre>
                  </div>
                )}

                {selectedHistoryItem.context && (
                  <div className="detail-item full">
                    <label>📎 컨텍스트</label>
                    <pre className="context-json">{JSON.stringify(selectedHistoryItem.context, null, 2)}</pre>
                  </div>
                )}

                {/* Previous Agent Results - Expandable */}
                {selectedHistoryItem.result?.data && (
                  <div className="detail-item full previous-results-section">
                    <label>📊 이전 에이전트 결과</label>
                    <div className="expandable-results">
                      {Object.entries(selectedHistoryItem.result.data).map(([key, value]) => {
                        if (!value || typeof value !== 'string' || value.length < 10) return null
                        const isExpanded = expandedResults[key]
                        const displayNames = {
                          plan: '📋 Plan 에이전트',
                          ux_ui: '🎨 UX/UI 에이전트',
                          architecture: '🏗️ Architect 에이전트',
                          code: '💻 Code 에이전트',
                          refactoring: '🔧 Refactoring 에이전트',
                          test_results: '🧪 TestQA 에이전트',
                          documentation: '📝 Doc 에이전트'
                        }
                        return (
                          <div key={key} className="expandable-result-card">
                            <div
                              className="result-header"
                              onClick={() => setExpandedResults(prev => ({ ...prev, [key]: !prev[key] }))}
                            >
                              <span className="result-title">{displayNames[key] || key}</span>
                              <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
                            </div>
                            {isExpanded && (
                              <div className="result-content">
                                <pre>{typeof value === 'string' ? value : JSON.stringify(value, null, 2)}</pre>
                              </div>
                            )}
                            {!isExpanded && (
                              <div className="result-preview">
                                {String(value).substring(0, 100)}...
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
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
