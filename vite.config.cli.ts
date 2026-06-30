import { defineConfig } from 'vite'
import { resolve } from 'node:path'

// Builds the headless render backend used by the Python CLI. SSR/Node mode so
// `node:fs` / `node:path` are preserved as real Node builtins. It bundles the
// REAL render pipeline (src/main/render/*) and persistence layer, resolving the
// `@shared` alias. `electron` is aliased to a stub (never touched at runtime —
// renderPages runs with save=false). `@napi-rs/canvas` and `smol-toml` stay
// external (resolved from node_modules at runtime).
export default defineConfig({
  resolve: {
    alias: {
      '@shared': resolve(__dirname, 'src/shared'),
      electron: resolve(__dirname, 'agent-harness/cli_src/electron-stub.js')
    }
  },
  build: {
    ssr: resolve(__dirname, 'agent-harness/cli_src/cli_render_entry.ts'),
    outDir: resolve(__dirname, 'agent-harness/cli_anything/handwrite/scripts'),
    emptyOutDir: false,
    minify: false,
    target: 'es2022',
    rollupOptions: {
      external: ['@napi-rs/canvas', 'smol-toml'],
      output: {
        format: 'es',
        entryFileNames: 'render_backend.mjs'
      }
    }
  }
})
