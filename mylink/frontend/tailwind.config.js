/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '-apple-system', 'BlinkMacSystemFont', 'SF Pro Text', 'SF Pro Display',
          'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'system-ui',
          'Apple Color Emoji', 'Segoe UI Emoji'
        ],
      },
      colors: {
        primary: {
          50:  '#EFF4FF',
          100: '#DFE8FF',
          200: '#BFD1FF',
          300: '#9EB9FF',
          400: '#6F95FF',
          500: '#4678FF',
          600: '#2E6BFF',
          700: '#2556CC',
          800: '#1C4099',
          900: '#132B66',
        },
        success: {
          50:  '#ECFDF3',
          400: '#32D583',
          600: '#12B76A',
          700: '#0E9F5B',
        },
        warning: {
          50:  '#FFFAEB',
          400: '#FEC84B',
          600: '#F79009',
        },
        danger: {
          50:  '#FEF3F2',
          400: '#F97066',
          600: '#EF4444',
        },
        grayx: {
          50:  '#F9FAFB',
          100: '#F2F4F7',
          200: '#EAECF0',
          300: '#E5E7EB',
          400: '#D0D5DD',
          500: '#98A2B3',
          600: '#475467',
          700: '#344054',
          800: '#1F2937',
          900: '#101828',
        },
      },
      borderRadius: {
        xs: '6px', sm: '8px', md: '10px', lg: '12px', xl: '16px', pill: '9999px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(16, 24, 40, 0.05)',
        md: '0 2px 8px rgba(16, 24, 40, 0.08)',
        lg: '0 8px 24px rgba(16, 24, 40, 0.12)',
      },
      ringColor: {
        focus: '#A4C2FF',
      },
      ringWidth: {
        3: '3px',
      },
      spacing: {
        0: '0px', 1: '4px', 2: '8px', 3: '12px', 4: '16px', 5: '20px', 6: '24px', 7: '28px', 8: '32px', 9: '40px', 10: '48px'
      },
    },
  },
  plugins: [],
}
