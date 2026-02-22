import './ProfileDropdown.css';

export default function ProfileDropdown({ onClose }) {
  return (
    <div className="profile-dropdown">
      <button
        className="profile-dropdown-item"
        onClick={() => {
          alert('Смена аккаунта (будет реализовано)');
          onClose();
        }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 8a3 3 0 100-6 3 3 0 000 6zM2 14a6 6 0 0112 0"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        Сменить аккаунт
      </button>
      <button
        className="profile-dropdown-item logout"
        onClick={() => {
          alert('Выход (будет реализовано)');
          onClose();
        }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M6 14H3.5A1.5 1.5 0 012 12.5v-9A1.5 1.5 0 013.5 2H6M11 11l3-3-3-3M14 8H6"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Выйти
      </button>
    </div>
  );
}
