/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Nova brand colors
        primary: '#f59e0b', // Amber-500 - main brand color
        'primary-dark': '#d97706', // Amber-600 - hover states
        'primary-light': '#fbbf24', // Amber-400 - accents
        secondary: '#64748b', // Slate-500
        'nova-orange': '#ea580c', // Orange-600
        'nova-glow': '#fef3c7', // Amber-100 - subtle backgrounds
      }
    },
  },
  plugins: [],
}
