/**
 * 登录态（token）与会话列表的本地存储管理。
 * token 由后端登录接口签发，供 API 请求认证。
 */
const TOKEN_KEY = 'data_agent_token'
const USERNAME_KEY = 'data_agent_username'
const SESSIONS_KEY = 'data_agent_sessions'
const CURRENT_SESSION_KEY = 'data_agent_current_session'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  return localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  return localStorage.removeItem(TOKEN_KEY)
}

export function isLoggedIn() {
  return !!getToken()
}

export function getUsername() {
  return localStorage.getItem(USERNAME_KEY) || ''
}

export function setUsername(name) {
  return localStorage.setItem(USERNAME_KEY, name)
}

export function clearLogin() {
  removeToken()
  localStorage.removeItem(USERNAME_KEY)
}

/** 生成本地会话 ID（后端要求 1-100 字符，用 32 位十六进制） */
export function generateSessionId() {
  let id = ''
  for (let i = 0; i < 32; i++) {
    id += Math.floor(Math.random() * 16).toString(16)
  }
  return id
}

/** 读取本地会话列表：[{ id, title, updatedAt }] */
export function getSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    const list = JSON.parse(raw || '[]')
    return Array.isArray(list) ? list : []
  } catch (e) {
    return []
  }
}

export function setSessions(sessions) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

/** 新会话入列（去重），标题默认取问题前 16 字 */
export function saveSession(sessionId, title) {
  if (!sessionId) return
  const sessions = getSessions().filter(s => s.id !== sessionId)
  sessions.unshift({
    id: sessionId,
    title: (title || '新会话').slice(0, 16),
    updatedAt: Date.now()
  })
  setSessions(sessions.slice(0, 50))
}

export function removeSession(sessionId) {
  setSessions(getSessions().filter(s => s.id !== sessionId))
}

export function getCurrentSessionId() {
  return localStorage.getItem(CURRENT_SESSION_KEY)
}

export function setCurrentSessionId(sessionId) {
  localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
}
