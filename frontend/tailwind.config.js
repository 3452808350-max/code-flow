/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#667eea',
          600: '#5a6fd8',
          700: '#4f46e5',
        },
        secondary: {
          500: '#764ba2',
        }
      }
    },
  },
  plugins: [],
}