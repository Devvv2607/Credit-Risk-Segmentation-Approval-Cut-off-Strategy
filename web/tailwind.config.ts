import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        border: "var(--border)",
        ink: "var(--ink)",
        muted: "var(--ink-muted)",
        accent: "var(--accent)",
        "warn-bg": "var(--warn-bg)",
        "warn-ink": "var(--warn-ink)",
        navy: "var(--series-1)",
        green: "var(--series-2)",
        rust: "var(--series-3)",
      },
      fontFamily: {
        sans: ["var(--font-space-grotesk)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      maxWidth: { prose: "1100px", wide: "1480px" },
    },
  },
  plugins: [],
};

export default config;
