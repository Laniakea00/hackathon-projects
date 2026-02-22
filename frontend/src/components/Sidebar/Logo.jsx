import './Logo.css';

export default function Logo() {
  return (
    <div className="logo">
      <div className="logo-icon">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="8" fill="#2563EB" />
          <path
            d="M14 7v14M7 14h14"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <span className="logo-text">QazCode</span>
    </div>
  );
}
