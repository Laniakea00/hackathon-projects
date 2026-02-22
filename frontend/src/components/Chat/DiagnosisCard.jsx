import './DiagnosisCard.css';

export default function DiagnosisCard({ diagnosis }) {
  const isPrimary = diagnosis.rank === 1;

  return (
    <div className={`diagnosis-card ${isPrimary ? 'primary' : ''}`}>
      <div className="diagnosis-rank">#{diagnosis.rank}</div>
      <div className="diagnosis-content">
        <div className="diagnosis-header">
          <span className="diagnosis-name">{diagnosis.name}</span>
          <span className="diagnosis-icd">{diagnosis.icd10}</span>
        </div>
        <p className="diagnosis-description">{diagnosis.description}</p>
      </div>
    </div>
  );
}
