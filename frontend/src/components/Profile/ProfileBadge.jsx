import { useState, useRef, useEffect } from 'react';
import ProfileDropdown from './ProfileDropdown';
import './ProfileBadge.css';

export default function ProfileBadge() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="profile-badge-wrapper" ref={ref}>
      <button className="profile-badge" onClick={() => setOpen(!open)}>
        <div className="profile-avatar">А</div>
        <span className="profile-name">Пользователь</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path
            d="M3 5l3 3 3-3"
            stroke="#6B7280"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {open && <ProfileDropdown onClose={() => setOpen(false)} />}
    </div>
  );
}
