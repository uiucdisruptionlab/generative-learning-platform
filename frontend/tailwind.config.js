/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#2c5926",
        forest: "#2c5926",
        "canvas-green": "#287D3C",
        "educational-teal": "#009688",
        secondary: "#f59e0b",
        accent: "#c2410c",
        "burnt-orange": "#cc5500",
        "warm-yellow": "#f4a900",
        "soft-teal": "#E0F2F1",
        "soft-yellow": "#FFF9C4",
        "warm-orange": "#FFE0B2",
        "background-light": "#fafaf9",
        "background-dark": "#1c1917",
        "primary-light": "#2D6A4F",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        logo: ["Plus Jakarta Sans", "sans-serif"],
        sans: ["Lexend", "Inter", "sans-serif"],
        serif: ["Syne", "sans-serif"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-card": "linear-gradient(135deg, rgba(44, 89, 38, 0.03) 0%, rgba(244, 169, 0, 0.03) 100%)",
        "gradient-warm": "linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%)",
        "gradient-accent": "linear-gradient(135deg, rgba(44, 89, 38, 0.08) 0%, rgba(204, 85, 0, 0.05) 100%)",
      },
      borderRadius: {
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        soft: "0 4px 20px -2px rgba(0, 0, 0, 0.05)",
        "hover-soft": "0 10px 25px -5px rgba(0, 0, 0, 0.08)",
      },
    },
  },
  plugins: [],
}
