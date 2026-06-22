import { createRouter, createWebHashHistory } from 'vue-router'
import EditorView from './components/EditorView.vue'
import PreviewView from './components/PreviewView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: EditorView },
    { path: '/preview', component: PreviewView }
  ]
})
