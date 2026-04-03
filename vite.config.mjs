import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const resolvePath = (...parts) => path.resolve(__dirname, ...parts);

export default defineConfig({
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
        archibald: resolvePath("core/static/core/archibald.js"),
        agenda: resolvePath("agenda/static/agenda/agenda.js"),
        subscriptions_dashboard: resolvePath("subscriptions/static/subscriptions/dashboard.js"),
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
