import Vue from 'vue'
import Router from 'vue-router'
import { isLoggedIn } from '../utils/auth'

Vue.use(Router)

const router = new Router({
  routes: [
    {
      path: '/',
      redirect: '/chat'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('../views/Chat.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: () => import('../views/Knowledge.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

// 全局导航钩子：未登录访问任何受保护页面 -> 登录页；已登录访问登录页 -> 对话页
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth !== false && !isLoggedIn()) {
    next('/login')
  } else if (to.path === '/login' && isLoggedIn()) {
    next('/chat')
  } else {
    next()
  }
})

export default router
