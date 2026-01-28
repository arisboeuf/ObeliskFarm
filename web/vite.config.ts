import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages serves project sites under "/<repo>/".
// We keep dev experience simple ("/") and let CI set BASE_PATH.
const base = process.env.BASE_PATH ?? "/";

export default defineConfig({
  plugins: [react()],
  base,
});

