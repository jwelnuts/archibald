import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const resolvePath = (...parts) => path.resolve(__dirname, ...parts);

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      "@core": resolvePath("core/static/core"),
    },
  },
  build: {
    outDir: resolvePath("core/static/core/dist"),
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      input: {
        app: resolvePath("core/static/core/app.js"),
        dashboard: resolvePath("core/static/core/dashboard.js"),
        transactions: resolvePath("core/static/core/transactions.js"),
        todo: resolvePath("core/static/core/todo.js"),
        routines: resolvePath("core/static/core/routines.js"),
        projects_storyboard: resolvePath("core/static/core/projects_storyboard.js"),
        projects_timeline: resolvePath("core/static/core/projects_timeline.js"),
        agenda: resolvePath("agenda/static/agenda/agenda.js"),
        subscriptions_dashboard: resolvePath("subscriptions/static/subscriptions/dashboard.js"),
        spa_dashboard: resolvePath("spa_dashboard/static/spa_dashboard/main.js"),
      },
      output: {
        format: "es",
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
