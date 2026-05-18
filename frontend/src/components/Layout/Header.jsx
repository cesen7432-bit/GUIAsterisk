import { LogOut, User, Wifi, WifiOff } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

export function Header({ amiConnected }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${
          amiConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {amiConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          AMI {amiConnected ? 'Conectado' : 'Desconectado'}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center">
            <User size={14} className="text-blue-600" />
          </div>
          <span className="font-medium">{user?.name}</span>
          <span className="text-xs text-gray-400 capitalize">({user?.role})</span>
        </div>
        <button onClick={handleLogout} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors">
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
