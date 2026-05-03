// Vitest config — separate from vite.config.js so we can keep the dev/build
// config focused. Reuses the same React plugin so JSX transforms match what
// production gets.
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,                            // describe/it/expect available without imports
    setupFiles: ['./src/__tests__/setup.js'],
    css: false,                               // CSS imports are no-ops in tests
    // Component tests live next to the components they cover under
    // src/__tests__/<component>.test.jsx. Excludes Playwright tests
    // (separate runner, separate dir).
    include: ['src/__tests__/**/*.test.{js,jsx}'],
    exclude: ['node_modules', 'dist', 'tests-e2e'],
    // Each component test should finish in milliseconds; if anything blows
    // past 5s it's a sign we accidentally hit a real timer or network.
    testTimeout: 5000,
  },
});
