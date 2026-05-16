import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/DashboardLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/pages/DashboardPage.vue'),
        },
        {
          path: 'batch/:id',
          name: 'batch-details',
          component: () => import('@/pages/BatchDetailsPage.vue'),
        },
        {
          path: 'upload',
          name: 'upload',
          component: () => import('@/pages/UploadPage.vue'),
        },
        {
          path: 'document/:id',
          name: 'review-document',
          component: () => import('@/pages/ReviewDocumentPage.vue'),
        },
      ],
    },
  ],
})

export default router
