import './LoadingIndicator.css';

export default function LoadingIndicator() {
  return (
    <div className="loading-wrapper">
      <div className="loading-indicator">
        <div className="loading-dot" />
        <div className="loading-dot" />
        <div className="loading-dot" />
      </div>
    </div>
  );
}
