// Author: Pradeep Sahoo — Retail Nexus AI
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f1f4fa",
          100: "#dbe3f0",
          200: "#b7c6e0",
          300: "#8ea5cd",
          400: "#6482b3",
          500: "#44679b",
          600: "#2f507d",
          700: "#243f63",
          800: "#1a2e49",
          900: "#121a2e",
          950: "#0b1220",
        },
        accent: {
          DEFAULT: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
