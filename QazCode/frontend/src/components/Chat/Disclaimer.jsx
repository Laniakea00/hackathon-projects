import './Disclaimer.css';

export default function Disclaimer() {
  return (
    <div className="disclaimer">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <circle cx="7" cy="7" r="6" stroke="#F59E0B" strokeWidth="1.5" />
        <path
          d="M7 4v3M7 9h.01"
          stroke="#F59E0B"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
      Ассистент не заменяет врача. Результат носит справочный характер.
    </div>
  );
}
