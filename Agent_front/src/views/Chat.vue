<template>
  <div class="chat-layout">
    <!-- 左侧：会话列表 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <span class="logo">企业数据 Agent</span>
      </div>
      <el-button
        type="primary"
        icon="el-icon-plus"
        size="small"
        class="new-session-btn"
        @click="createSession"
      >新建会话</el-button>
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === currentSessionId }"
          @click="switchSession(session.id)"
        >
          <i class="el-icon-chat-dot-round session-icon"></i>
          <span class="session-title" :title="session.title">{{ session.title }}</span>
          <i
            class="el-icon-delete session-delete"
            @click.stop="removeSession(session.id)"
          ></i>
        </div>
      </div>
      <div class="sidebar-footer">
        <div class="footer-user">
          <i class="el-icon-user-solid"></i>
          <span>{{ username }}</span>
        </div>
        <div class="footer-actions">
          <el-button type="text" icon="el-icon-reading" @click="$router.push('/knowledge')">
            知识库管理
          </el-button>
          <el-button type="text" icon="el-icon-switch-button" @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </div>
    </div>

    <!-- 右侧：对话区 -->
    <div class="chat-main">
      <div class="chat-header">
        <h1>智能数据分析</h1>
        <span class="header-sub">自然语言提问，自动完成查询、检索与分析</span>
      </div>

      <div class="message-list" ref="messageList">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="message-item"
          :class="{ 'user-message': msg.role === 'user', 'ai-message': msg.role === 'assistant' }"
        >
          <div class="message-avatar">
            <i :class="msg.role === 'user' ? 'el-icon-user' : 'el-icon-magic-stick'"></i>
          </div>
          <div class="message-content">
            <!-- 执行步骤时间线：流式过程中实时展示，回答完成后自动收起 -->
            <div v-if="msg.steps && msg.steps.length && msg.showSteps" class="steps-panel">
              <div class="steps-toggle" @click="msg.showSteps = false">
                <i class="el-icon-arrow-up"></i> 收起执行过程
              </div>
              <div v-for="step in msg.steps" :key="step.node" class="step-row">
                <i
                  :class="step.status === 'running'
                    ? 'el-icon-loading step-running'
                    : 'el-icon-success step-done'"
                ></i>
                <span class="step-title">{{ step.title }}</span>
                <span class="step-desc">{{ step.description }}</span>
              </div>
            </div>
            <div
              v-else-if="msg.steps && msg.steps.length"
              class="steps-collapsed"
              @click="msg.showSteps = true"
            >
              <i class="el-icon-arrow-right"></i> 执行过程（{{ msg.steps.length }} 步）
            </div>

            <div v-if="msg.role === 'user'" class="message-text">{{ msg.content }}</div>
            <div v-else class="message-text markdown-body" v-html="renderMarkdown(msg.content)"></div>

            <div v-if="msg.taskType" class="message-meta">
              <el-tag size="mini" type="info">{{ taskTypeLabel(msg.taskType) }}</el-tag>
              <el-tag v-if="msg.status === 'failed'" size="mini" type="danger">执行出错</el-tag>
            </div>
          </div>
        </div>

        <div v-if="loading && !streamingMessage" class="message-item ai-message">
          <div class="message-avatar">
            <i class="el-icon-magic-stick"></i>
          </div>
          <div class="message-content">
            <div class="message-text typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="例如：上季度各区域销售额对比，画个柱状图"
            :disabled="loading"
            @keydown.enter.exact.prevent="sendMessage"
            resize="none"
          ></el-input>
          <el-button
            type="primary"
            icon="el-icon-s-promotion"
            :loading="loading"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          ></el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { streamAgent, fetchConversation, deleteConversation } from '../api/agent'
import {
  getUsername, clearLogin,
  getSessions, saveSession, removeSession, setCurrentSessionId, getCurrentSessionId,
  generateSessionId
} from '../utils/auth'

marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {}
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

const TASK_TYPE_LABELS = {
  knowledge_query: '知识问答',
  data_query: '数据查询',
  complex_analysis: '复杂分析',
  chart_followup: '图表追问'
}

export default {
  name: 'Chat',
  data() {
    return {
      sessions: getSessions(),
      currentSessionId: '',
      username: getUsername(),
      messages: [],
      inputMessage: '',
      loading: false,
      streamingMessage: null
    }
  },
  mounted() {
    const saved = getCurrentSessionId()
    if (saved && this.sessions.some(s => s.id === saved)) {
      this.switchSession(saved)
    } else {
      this.createSession()
    }
  },
  methods: {
    renderMarkdown(text) {
      if (!text) return ''
      return marked.parse(text)
    },
    taskTypeLabel(type) {
      return TASK_TYPE_LABELS[type] || type
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messageList
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },
    pushAssistantWelcome() {
      this.messages = [{
        role: 'assistant',
        content: '你好！我是企业数据分析助手，可以直接用自然语言提问，例如：\n\n- 上季度各区域销售额对比\n- 销售毛利率是怎么定义的？\n- 最近 30 天订单趋势，画个折线图',
        steps: [],
        taskType: null,
        status: null
      }]
    },
    createSession() {
      this.currentSessionId = generateSessionId()
      setCurrentSessionId(this.currentSessionId)
      saveSession(this.currentSessionId, '新会话')
      this.sessions = getSessions()
      this.pushAssistantWelcome()
    },
    async switchSession(sessionId) {
      if (this.loading) {
        this.$message.warning('当前问题还在回答中，请稍候再切换')
        return
      }
      this.currentSessionId = sessionId
      setCurrentSessionId(sessionId)
      this.pushAssistantWelcome()
      try {
        const res = await fetchConversation(sessionId)
        if (res && res.messages && res.messages.length) {
          this.messages = res.messages.map(m => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content || '',
            steps: [],
            taskType: null,
            status: null
          }))
        }
      } catch (e) {
        // 会话历史读取失败不阻断，保留欢迎语
      }
      this.scrollToBottom()
    },
    removeSession(sessionId) {
      if (this.loading) {
        this.$message.warning('当前问题还在回答中，请稍候再删除')
        return
      }
      this.$confirm('确定删除该会话及其短期记忆吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        await deleteConversation(sessionId)
        removeSession(sessionId)
        this.sessions = getSessions()
        if (sessionId === this.currentSessionId) {
          if (this.sessions.length) {
            this.switchSession(this.sessions[0].id)
          } else {
            this.createSession()
          }
        }
        this.$message.success('会话及短期记忆已删除')
      }).catch(() => {})
    },
    // ---- 流式步骤维护 ----
    findStep(steps, node) {
      for (let i = steps.length - 1; i >= 0; i--) {
        if (steps[i].node === node) return steps[i]
      }
      return null
    },
    handleStepStart(msg, payload) {
      // 同一 node 的 step_start 可能因嵌套 chain 重复触发，按 node 去重
      const existing = this.findStep(msg.steps, payload.node)
      if (existing) {
        existing.status = 'running'
        return
      }
      msg.steps.push({
        node: payload.node,
        title: payload.title,
        description: payload.description,
        status: 'running'
      })
    },
    handleStepEnd(msg, payload) {
      const step = this.findStep(msg.steps, payload.node)
      if (step) step.status = 'done'
    },
    // ---- 发送与流式接收 ----
    async sendMessage() {
      const message = this.inputMessage.trim()
      if (!message || this.loading) return

      this.messages.push({
        role: 'user',
        content: message,
        steps: [],
        taskType: null,
        status: null
      })
      // 用问题更新会话标题（新会话默认叫"新会话"）
      saveSession(this.currentSessionId, message)
      this.sessions = getSessions()
      this.inputMessage = ''
      this.loading = true
      this.scrollToBottom()

      const assistantMessage = {
        role: 'assistant',
        content: '',
        steps: [],
        showSteps: true,
        taskType: null,
        status: null
      }
      this.messages.push(assistantMessage)
      this.streamingMessage = assistantMessage
      const messageIndex = this.messages.length - 1
      this.scrollToBottom()

      try {
        await streamAgent(message, this.currentSessionId, {
          onStart: () => {
            this.scrollToBottom()
          },
          onStepStart: payload => {
            this.handleStepStart(assistantMessage, payload)
            this.scrollToBottom()
          },
          onStepEnd: payload => {
            this.handleStepEnd(assistantMessage, payload)
          },
          // 工具事件（tool_start/tool_end）不展示：
          // 不向前端暴露内部工具/函数名，仅保留业务化步骤描述。
          onChunk: payload => {
            assistantMessage.content += payload.content || ''
            this.$set(this.messages, messageIndex, assistantMessage)
            this.scrollToBottom()
          },
          onMetadata: payload => {
            assistantMessage.taskType = payload.task_type || null
            assistantMessage.status = payload.status || null
            if (payload.errors && payload.errors.length) {
              this.$message.warning('部分步骤出现问题：' + payload.errors[0])
            }
          },
          onError: payload => {
            this.$message.error((payload && payload.message) || '执行出错')
          }
        })
      } catch (error) {
        console.error('流式请求失败:', error)
        if (!assistantMessage.content) {
          assistantMessage.content = '抱歉，请求失败，请确认后端服务已启动后重试。'
        }
        this.$set(this.messages, messageIndex, assistantMessage)
      } finally {
        // 回答完成：自动收起执行步骤，保持消息区整洁（可点"执行过程"回看）
        this.$set(assistantMessage, 'showSteps', false)
        this.$set(this.messages, messageIndex, assistantMessage)
        // 图表追问等场景可能整段没有 chunk（答案只在 metadata 里），兜底提示
        if (!assistantMessage.content) {
          assistantMessage.content = '本轮未生成文本回答，可稍后重试或换个问法。'
          this.$set(this.messages, messageIndex, assistantMessage)
        }
        this.loading = false
        this.streamingMessage = null
        this.scrollToBottom()
      }
    },
    handleLogout() {
      this.$confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        clearLogin()
        this.$router.push('/login')
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  background: #f3f6fb;
}

/* ---------- 左侧侧栏 ---------- */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #1f2937;
  color: #d1d5db;
}

.sidebar-header {
  padding: 18px 16px 12px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.new-session-btn {
  margin: 4px 12px 12px;
  width: calc(100% - 24px);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  font-size: 13px;
}

.session-item:hover {
  background: #374151;
}

.session-item.active {
  background: #2563eb;
  color: #fff;
}

.session-icon {
  margin-right: 8px;
  flex-shrink: 0;
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-delete {
  visibility: hidden;
  margin-left: 6px;
  flex-shrink: 0;
}

.session-item:hover .session-delete {
  visibility: visible;
}

.sidebar-footer {
  border-top: 1px solid #374151;
  padding: 12px 16px;
}

.footer-user {
  font-size: 13px;
  margin-bottom: 6px;
  color: #9ca3af;
}

.footer-user i {
  margin-right: 6px;
}

.footer-actions {
  display: flex;
  justify-content: space-between;
}

.footer-actions .el-button {
  color: #d1d5db;
  padding: 4px 0;
}

.footer-actions .el-button:hover {
  color: #fff;
}

/* ---------- 右侧对话区 ---------- */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 14px 32px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e5eaf3;
  box-shadow: 0 10px 30px rgba(31, 41, 55, 0.05);
  z-index: 10;
}

.chat-header h1 {
  color: #111827;
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.header-sub {
  color: #909399;
  font-size: 13px;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 28px 28px 24px;
}

.message-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 18px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 17px;
  color: #fff;
  box-shadow: 0 8px 18px rgba(31, 41, 55, 0.12);
}

.user-message .message-avatar {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.ai-message .message-avatar {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.message-content {
  max-width: min(78%, 720px);
  margin: 0 12px;
  text-align: left;
}

.user-message .message-content {
  background: #2563eb;
  color: #fff;
  border-radius: 16px 16px 4px 16px;
  padding: 11px 16px;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
}

.ai-message .message-content {
  background: #fff;
  color: #1f2937;
  border: 1px solid #e6ebf2;
  border-radius: 16px 16px 16px 4px;
  padding: 12px 16px;
  box-shadow: 0 10px 26px rgba(31, 41, 55, 0.06);
}

.message-text {
  line-height: 1.6;
  word-break: break-word;
  text-align: left;
}

.user-message .message-text {
  white-space: pre-wrap;
}

/* ---------- 执行步骤面板 ---------- */
.steps-panel {
  border-bottom: 1px dashed #e5eaf3;
  padding-bottom: 8px;
  margin-bottom: 10px;
}

.step-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
  padding: 3px 0;
}

.step-running {
  color: #2563eb;
}

.step-done {
  color: #10b981;
}

.step-title {
  font-weight: 600;
  color: #374151;
}

.step-desc {
  color: #9ca3af;
}

.steps-toggle {
  font-size: 12px;
  color: #2563eb;
  cursor: pointer;
  margin-bottom: 4px;
  user-select: none;
}

.steps-collapsed {
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
  margin-bottom: 8px;
  user-select: none;
}

.steps-collapsed:hover {
  color: #2563eb;
}

.message-meta {
  margin-top: 8px;
}

/* ---------- markdown ---------- */
.markdown-body {
  font-size: 14px;
  text-align: left;
  white-space: normal;
  overflow-wrap: anywhere;
}

.markdown-body >>> h1,
.markdown-body >>> h2,
.markdown-body >>> h3 {
  margin: 12px 0 8px;
  color: #111827;
  line-height: 1.35;
}

.markdown-body >>> p {
  margin: 0 0 10px;
}

.markdown-body >>> p:last-child {
  margin-bottom: 0;
}

.markdown-body >>> pre {
  background: #0f172a;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
}

.markdown-body >>> code {
  background: #eef2f7;
  color: #334155;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.markdown-body >>> pre code {
  background: none;
  color: inherit;
  padding: 0;
}

.markdown-body >>> ul,
.markdown-body >>> ol {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body >>> blockquote {
  border-left: 4px solid #ddd;
  padding-left: 16px;
  color: #666;
  margin: 8px 0;
}

.markdown-body >>> table {
  border-collapse: collapse;
  margin: 10px 0;
  width: 100%;
  font-size: 13px;
  display: block;
  overflow-x: auto;
  white-space: nowrap;
}

.markdown-body >>> th,
.markdown-body >>> td {
  border: 1px solid #e5eaf3;
  padding: 6px 10px;
  text-align: left;
}

.markdown-body >>> th {
  background: #f8fafc;
  font-weight: 600;
  color: #374151;
}

.markdown-body >>> tr:nth-child(2n) td {
  background: #fafbfc;
}

.markdown-body >>> img {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 12px auto;
  border-radius: 8px;
}

/* ---------- 打字动画 ---------- */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 18px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #c0c4cc;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* ---------- 输入区 ---------- */
.input-area {
  padding: 18px 28px 22px;
  background: rgba(255, 255, 255, 0.95);
  border-top: 1px solid #e5eaf3;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  max-width: 980px;
  margin: 0 auto;
}

.input-wrapper .el-textarea {
  flex: 1;
}

.input-wrapper .el-button {
  height: 54px;
  width: 54px;
  padding: 0;
  font-size: 20px;
}

>>> .el-textarea__inner {
  min-height: 54px !important;
  border-radius: 12px;
  border: 1px solid #d8dee9;
  box-shadow: 0 8px 20px rgba(31, 41, 55, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}

>>> .el-textarea__inner:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .chat-header {
    padding: 12px 16px;
  }

  .message-list {
    padding: 20px 14px;
  }

  .message-content {
    max-width: calc(100% - 56px);
    margin: 0 8px;
  }

  .input-area {
    padding: 12px 14px 16px;
  }
}
</style>
