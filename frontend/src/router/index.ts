import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { requiresAuth: true, title: '仪表盘' }
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('@/views/Accounts.vue'),
        meta: { requiresAuth: true, title: '账号管理' }
      },
      {
        path: 'media',
        name: 'Media',
        component: () => import('@/views/Media.vue'),
        meta: { requiresAuth: true, title: '媒体管理' }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('@/views/Analytics.vue'),
        meta: { requiresAuth: true, title: '数据分析' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { requiresAuth: true, title: '任务监控' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { requiresAuth: true, title: '系统设置' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && userStore.isLoggedIn) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
