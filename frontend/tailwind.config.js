/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#071219",
        surface: "#0d1a24",
        card: "#112332",
        border: "#1f3b4b",

        textPrimary: "#e7f7f8",
        textSecondary: "#a7c7ce",
        textMuted: "#6f98a0",

        accent: "#14b8a6",
        accentCyan: "#22d3ee",
        accentDeep: "#0f766e",

        threat: {
          critical: "#ef4444",
          high: "#f97316",
          medium: "#facc15",
          low: "#22c55e",
          info: "#38bdf8"
        },
      },
    },
  },
  plugins: [],
};
