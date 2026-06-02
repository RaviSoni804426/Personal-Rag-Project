/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "Outfit", "ui-sans-serif", "system-ui"],
        outfit: ["Outfit", "sans-serif"],
      },
      colors: {
        slate: {
          850: "#151f32",
          750: "#223147",
        }
      }
    },
  },
  plugins: [],
}
