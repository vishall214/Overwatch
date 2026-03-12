/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ow: {
          bg: "#04161F",
          surface: "#061E29",
          panel: "#0C2E3A",
          accent: "#2BB6C9",
          "accent-dim": "#1FA0B3",
          teal: "#1D546D",
          mist: "#5F9598",
          light: "#F3F4F4",
          glass: "rgba(29,84,109,0.32)",
          "alert-intrusion": "#FF4D4D",
          "alert-loitering": "#FF9F40",
          "alert-crowd": "#3BA8FF",
        },
      },
      backdropBlur: {
        glass: "18px",
      },
      boxShadow: {
        glass: "0 8px 30px rgba(0,0,0,0.35)",
        glow: "0 0 20px rgba(43,182,201,0.15)",
        "glow-hover": "0 0 30px rgba(43,182,201,0.35)",
      },
      borderColor: {
        "glass-border": "rgba(255,255,255,0.08)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scan": "scan 3s ease-in-out infinite",
      },
      keyframes: {
        scan: {
          "0%, 100%": { opacity: "0.3" },
          "50%": { opacity: "0.8" },
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
