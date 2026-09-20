/**
 * Agent 问答接口：同步分析 + 会话历史 + NDJSON 流式问答。
 *
 * 流式协议（POST /v1/agent/stream，每行一个 JSON 事件）：
 *   start       { task_id, session_id }
 *   step_start  { node, title, description }   Agent 步骤开始
 *   step_end    { node, title, description }   Agent 步骤结束
 *   chunk       { node, content }              答案文本分片（打字机追加）
 *   metadata    { task_type, route, status, errors, ... }
 *   error       { message }
 *   done        流结束
 *
 * 注：后端已不再下发 tool_start/tool_end 事件（工具名/入参不外发，
 * 工具观测仅在服务端日志记录）；下方 switch 中的分支仅作兼容保留。
 */
import request from '../utils/request'
import { getToken, clearLogin } from '../utils/auth'

const BASE_URL = '/v1'

/** 同步问答（调试用）：返回完整 AgentAnalyzeResponse */
export function analyzeQuestion(data) {
  return request({ url: '/agent/analyze', method: 'post', data: data })
}

/** 读取指定会话的历史对话（checkpointer 存储） */
export function fetchConversation(sessionId) {
  return request({ url: '/memory/sessions/' + encodeURIComponent(sessionId), method: 'get' })
}

/** 删除指定会话在后端 Redis 中的短期记忆 */
export function deleteConversation(sessionId) {
  return request({ url: '/memory/sessions/' + encodeURIComponent(sessionId), method: 'delete' })
}

/**
 * 流式问答。handlers 为事件回调集合，均可选：
 *   onStart / onStepStart / onStepEnd / onToolStart / onToolEnd /
 *   onChunk / onMetadata / onError / onDone
 */
export async function streamAgent(question, sessionId, handlers) {
  const h = handlers || {}
  const response = await fetch(BASE_URL + '/agent/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + (getToken() || '')
    },
    body: JSON.stringify({ question: question, session_id: sessionId })
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearLogin()
      window.location.href = '/#/login'
    }
    throw new Error('请求失败（HTTP ' + response.status + '）')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  // NDJSON：按换行切分，半行留在 buffer 等下一个数据块
  const dispatchLine = line => {
    const text = line.trim()
    if (!text) return
    let evt
    try {
      evt = JSON.parse(text)
    } catch (e) {
      return
    }
    switch (evt.event) {
      case 'start':
        if (h.onStart) h.onStart(evt)
        break
      case 'step_start':
        if (h.onStepStart) h.onStepStart(evt)
        break
      case 'step_end':
        if (h.onStepEnd) h.onStepEnd(evt)
        break
      case 'tool_start':
        if (h.onToolStart) h.onToolStart(evt)
        break
      case 'tool_end':
        if (h.onToolEnd) h.onToolEnd(evt)
        break
      case 'chunk':
        if (h.onChunk) h.onChunk(evt)
        break
      case 'metadata':
        if (h.onMetadata) h.onMetadata(evt)
        break
      case 'error':
        if (h.onError) h.onError(evt)
        break
      case 'done':
        if (h.onDone) h.onDone(evt)
        break
      default:
        break
    }
  }

  while (true) {
    const result = await reader.read()
    if (result.done) break
    buffer += decoder.decode(result.value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 1)
      dispatchLine(line)
    }
  }
  // 收尾：最后一段无换行的残包
  dispatchLine(buffer)
}
