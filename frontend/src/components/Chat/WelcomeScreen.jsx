import './WelcomeScreen.css';

export default function WelcomeScreen() {
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="16" fill="#EFF6FF" />
          <path
            d="M24 14v20M14 24h20"
            stroke="#2563EB"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <h1 className="welcome-title">Чем я могу помочь?</h1>
      <p className="welcome-subtitle">
        Опишите ваши симптомы, и я предложу возможные диагнозы
      </p>
    </div>
  );
}
