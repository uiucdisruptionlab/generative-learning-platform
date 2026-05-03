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
        // UIUC Illini — primary brand
        primary: "#FF5F05",
        "primary-hover": "#E55604",
        forest: "#FF5F05",
        "primary-light": "#FCB316",
        illini: {
          blue: "#13294B",
          orange: "#FF5F05",
        },
        // Secondary — Storm neutrals (backgrounds, text blocks)
        storm: {
          700: "#707372",
          500: "#9C9A9D",
          300: "#C8C6C7",
        },
        // Supporting — outlines & accents (Industrial, Arches, Patina, etc.)
        industrial: "#1D58A7",
        arches: "#009FD4",
        patina: "#007E8E",
        berry: "#5C0E41",
        harvest: "#FCB316",
        prairie: "#006230",
        earth: "#7D3E13",
        "canvas-green": "#1D58A7",
        "educational-teal": "#009FD4",
        secondary: "#FCB316",
        accent: "#13294B",
        "burnt-orange": "#FF5F05",
        "warm-yellow": "#FCB316",
        "soft-teal": "#E8F4FC",
        "soft-yellow": "#FFF8E8",
        "warm-orange": "#FFE8D6",
        "background-light": "#fafaf9",
        "background-dark": "#13294B",
      },
      fontFamily: {
        display: ["DM Sans", "sans-serif"],
        logo: ["DM Sans", "sans-serif"],
        sans: ["Inter", "Lexend", "sans-serif"],
        serif: ["DM Sans", "sans-serif"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-card":
          "linear-gradient(135deg, rgba(19, 41, 75, 0.04) 0%, rgba(255, 95, 5, 0.04) 100%)",
        "gradient-warm":
          "linear-gradient(135deg, #fafaf9 0%, #f0eeef 50%, #fafaf9 100%)",
        "gradient-accent":
          "linear-gradient(135deg, rgba(19, 41, 75, 0.07) 0%, rgba(255, 95, 5, 0.06) 100%)",
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
