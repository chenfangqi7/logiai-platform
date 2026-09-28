import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import AdminLayout from '../layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginView },
    { path: '/', component: AdminLayout, meta: { requiresAuth: true }, children: [
      { path: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'connectors', component: () => import('../views/ConnectorsView.vue') },
      { path: 'connectors/create', component: () => import('../views/ConnectorCreateView.vue') },
      { path: 'connectors/:id', component: () => import('../views/ConnectorDetailView.vue') },
      { path: 'connectors/:id/mapping', component: () => import('../views/MappingView.vue') },
      { path: 'shipments', component: () => import('../views/ShipmentsView.vue') },
      { path: 'shipments/:id', component: () => import('../views/ShipmentDetailView.vue') },
      { path: 'exceptions', component: () => import('../views/ExceptionsView.vue') },
      { path: 'exceptions/:id', component: () => import('../views/ExceptionDetailView.vue') },
      { path: 'ai', component: () => import('../views/AIView.vue') },
      { path: 'ai-usage', component: () => import('../views/AIUsageView.vue') },
      { path: 'knowledge', component: () => import('../views/KnowledgeView.vue') },
      { path: 'settings', component: () => import('../views/SettingsView.vue') },
    ] },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const token = sessionStorage.getItem('logiai_access_token')
  if (to.meta.requiresAuth) {
    if (!token) return { path: '/login', query: { redirect: to.fullPath } }
    if (!auth.user) {
      try {
        await auth.loadUser()
      } catch {
        auth.logout()
        return { path: '/login', query: { redirect: to.fullPath } }
      }
    }
  }
  if (to.path === '/login' && token && auth.user) return '/dashboard'
})

export default router
