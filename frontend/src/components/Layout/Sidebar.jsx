import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Phone, PhoneCall, PhoneIncoming, PhoneOutgoing,
  Layers, Users, GitBranch, Voicemail, Mic, FileText, Ban,
  Calendar, Volume2, Settings, Shield, Activity, Radio, PhoneForwarded,
} from 'lucide-react'
import clsx from 'clsx'

const menu = [
  { label: 'Dashboard',     path: '/',                icon: LayoutDashboard },
  { label: 'Monitor',       path: '/monitor',         icon: Activity },
  { section: 'Telefonía' },
  { label: 'Extensiones',   path: '/extensions',      icon: Phone },
  { label: 'Troncales',     path: '/trunks',          icon: Radio },
  { label: 'Rutas Salida',  path: '/routes/outbound', icon: PhoneOutgoing },
  { label: 'Rutas Entrada', path: '/routes/inbound',  icon: PhoneIncoming },
  { label: 'IVR',           path: '/ivr',             icon: Layers },
  { label: 'Sígueme',       path: '/followme',        icon: PhoneForwarded },
  { label: 'Colas',         path: '/queues',          icon: Users },
  { section: 'Registros' },
  { label: 'CDR',           path: '/cdr',             icon: FileText },
  { label: 'Grabaciones',   path: '/recordings',      icon: Mic },
  { label: 'Buzón de Voz',  path: '/voicemail',       icon: Voicemail },
  { section: 'Configuración' },
  { label: 'Lista Negra',   path: '/blacklist',       icon: Ban },
  { label: 'Horarios',      path: '/schedules',       icon: Calendar },
  { label: 'Audios',        path: '/sounds',          icon: Volume2 },
  { label: 'Usuarios GUI',  path: '/users',           icon: GitBranch },
  { label: 'Usuarios ARI',  path: '/ari',             icon: Shield },
  { label: 'Sistema',       path: '/system',          icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="w-60 bg-gray-900 text-gray-300 flex flex-col min-h-screen">
      <div className="px-6 py-5 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
            <Phone size={18} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">Asterisk</p>
            <p className="text-gray-400 text-xs">PBX Manager</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
        {menu.map((item, i) => {
          if (item.section) {
            return (
              <div key={i} className="px-3 pt-4 pb-1">
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-500">
                  {item.section}
                </p>
              </div>
            )
          }
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <Icon size={16} />
              {item.label}
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}
