/**
 * axios 实例：统一 baseURL（不走 devServer 代理）+ token 请求头 + 401 处理。
 * 注意：流式接口 /agent/stream 不走 axios（axios 拿不到流式响应体），
 * 见 src/api/agent.js 的 fetch 实现。
 */
import axios from 'axios'
import { getToken, clearLogin } from './auth'
import { Message } from 'element-ui'
import router from '../router'

const service = axios.create({
  baseURL: '/v1',
  timeout: 30000
})

service.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        clearLogin()
        router.push('/login')
        Message.error('登录已过期，请重新登录')
      } else if (status === 403) {
        Message.error('没有权限访问')
      } else if (status === 500) {
        Message.error('服务器错误')
      } else {
        const data = error.response.data
        let detail = ''
        if (data && data.detail) {
          detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        }
        Message.error(detail || '请求失败')
      }
    } else {
      Message.error('网络连接失败，请确认服务已启动')
    }
    return Promise.reject(error)
  }
)

export default service
