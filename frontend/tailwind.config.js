/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Syne', 'sans-serif'],
      },
      colors: {
        'bg-base':       'var(--bg-base)',
        'bg-surface':    'var(--bg-surface)',
        'bg-elevated':   'var(--bg-elevated)',
        'bg-card':       'var(--bg-card)',
        'border-col':    'var(--border)',
        'border-subtle': 'var(--border-subtle)',
        'text-primary':  'var(--text-primary)',
        'text-secondary':'var(--text-secondary)',
        'text-muted':    'var(--text-muted)',
        'accent':        'var(--accent)',
        'accent-dim':    'var(--accent-dim)',
        'status-red':    'var(--red)',
        'status-green':  'var(--green)',
        'status-yellow': 'var(--yellow)',
        'status-blue':   'var(--blue)',
        'status-purple': 'var(--purple)',
        'red-dim':       'var(--red-dim)',
        'green-dim':     'var(--green-dim)',
        'yellow-dim':    'var(--yellow-dim)',
        'blue-dim':      'var(--blue-dim)',
        'purple-dim':    'var(--purple-dim)',
      },
      borderRadius: {
        card: '12px',
      },
      boxShadow: {
        card: 'var(--shadow)',
      },
    },
  },
  plugins: [],
}
