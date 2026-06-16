import DiagnosisCard from './DiagnosisCard';
import './AiResponse.css';

export default function AiResponse({ diagnoses }) {
  return (
    <div className="ai-response-wrapper">
      <div className="ai-response">
        <div className="ai-response-header">
          <div className="ai-avatar">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M9 3v12M3 9h12"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <span className="ai-name">AI-ассистент</span>
        </div>
        <p className="ai-intro">На основе описанных симптомов, возможные диагнозы:</p>
        <div className="diagnosis-list">
          {diagnoses.map((d) => (
            <DiagnosisCard key={d.rank} diagnosis={d} />
          ))}
        </div>
        <div className="ai-disclaimer-inline">
          Результат носит справочный характер и не является медицинским заключением.
        </div>
      </div>
    </div>
  );
}
