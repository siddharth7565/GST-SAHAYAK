/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gst: {
          orange: {
            DEFAULT: '#F4A261',
            light: '#FDE8D2',
            verylight: '#FFF3E8',
            deep: '#D97745',
            hover: '#e28e4a',
          },
          cream: '#FFF8F0',
          dark: '#2B211B',
          muted: '#7A6B63',
          border: '#E8DEC4',
          subtle: '#FAF4EB',
          green: '#6B8E6B',
          red: '#C96B5B',
        }
      },
      boxShadow: {
        'gst-subtle': '0 2px 8px -2px rgba(43, 33, 27, 0.05), 0 1px 3px 0 rgba(43, 33, 27, 0.03)',
        'gst-card': '0 4px 16px -4px rgba(217, 119, 69, 0.08), 0 2px 6px -2px rgba(43, 33, 27, 0.04)',
        'gst-elevated': '0 10px 25px -5px rgba(217, 119, 69, 0.12), 0 8px 10px -6px rgba(43, 33, 27, 0.04)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
};
