import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api/monitor': {
                target: 'http://localhost:8011',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/monitor/, ''),
            },
            '/api/broker': {
                target: 'http://localhost:8002',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/broker/, ''),
            },
            '/api/dispatcher': {
                target: 'http://localhost:8003',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/dispatcher/, ''),
            },
            '/api/fault-injector': {
                target: 'http://localhost:8004',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/fault-injector/, ''),
            },
            '/api/aas': {
                target: 'http://localhost:4001',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api\/aas/, ''),
            },
        },
    },
})
