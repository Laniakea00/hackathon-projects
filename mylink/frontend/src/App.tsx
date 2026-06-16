import { BrowserRouter, Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import EmployerAdmin from './pages/EmployerAdmin'
import CandidateWidget from './pages/CandidateWidget'
import Catalog from './pages/Catalog'
import Auth from './pages/Auth'
import { getRole, logoutAll } from './lib/api'
import ResumeEditor from './pages/ResumeEditor'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="h-[64px] border-b border-grayx-300 bg-white">
          <div className="container h-full flex items-center justify-between">
            <Link to="/" className="font-semibold text-[18px] tracking-[-0.01em]">
              <span className="text-[#111827]">my</span>
              <span className="text-primary-600">link</span>
            </Link>
            <HeaderNav />
          </div>
        </header>
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<AuthGate />} />
            <Route path="/resume" element={<ResumeEditor />} />
            <Route path="/employer-admin" element={<RequireRole role="employer"><EmployerAdmin /></RequireRole>} />
            <Route path="/widget" element={<CandidateWidget />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-grayx-300 bg-white text-center text-xs text-grayx-600 py-3">MyLink — HR Assistant</footer>
      </div>
    </BrowserRouter>
  )
}

export default App

function HeaderNav() {
  const nav = useNavigate()
  const role = getRole()
  return (
    <nav className="space-x-4 text-sm">
      {role === 'candidate' && <Link to="/" className="text-grayx-600 hover:text-grayx-900">Соискателям</Link>}
      {role === 'employer' && <Link to="/employer-admin" className="text-grayx-600 hover:text-grayx-900">Работодателям</Link>}
      {role && <button className="text-grayx-600 hover:text-grayx-900" onClick={() => { logoutAll(); nav('/auth') }}>Выйти</button>}
    </nav>
  )
}

function RequireRole({ role, children }: { role: 'employer' | 'candidate'; children: React.ReactElement }) {
  const current = getRole()
  if (current !== role) return <Navigate to="/auth" replace />
  return children
}

function AuthGate() {
  const role = getRole()
  const location = useLocation()
  if (!role) return <Navigate to="/auth" replace state={{ from: location }} />
  return role === 'employer' ? <Navigate to="/employer-admin" replace /> : <Catalog />
}
