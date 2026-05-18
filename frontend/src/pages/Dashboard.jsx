import { useQuery } from '@tanstack/react-query'
import { Phone, PhoneCall, PhoneMissed, Radio, Users, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../api/client'

function StatCard({ icon: Icon, label, value, color = 'blue', sub }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-green-50 text-green-600',
    red:    'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <div className="card flex items-center gap-5">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colors[color]}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get('/system/status').then(r => r.data),
    refetchInterval: 5000,
  })

  const { data: channels = [] } = useQuery({
    queryKey: ['active-channels'],
    queryFn: () => api.get('/system/active-calls').then(r => r.data),
    refetchInterval: 3000,
  })

  const { data: cdrStats } = useQuery({
    queryKey: ['cdr-stats'],
    queryFn: () => api.get('/cdr/stats').then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: extensions = [] } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => api.get('/extensions/').then(r => r.data),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm">Estado general del sistema</p>
      </div>

      {/* Status */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Estado Asterisk"
          value={status?.ari_connected ? 'Online' : 'Offline'}
          color={status?.ari_connected ? 'green' : 'red'} />
        <StatCard icon={PhoneCall} label="Llamadas activas"
          value={channels.length} color="blue" />
        <StatCard icon={Phone} label="Extensiones"
          value={extensions.length} color="purple" />
        <StatCard icon={PhoneMissed} label="Perdidas hoy"
          value={cdrStats?.no_answer ?? 0} color="red"
          sub={`Total: ${cdrStats?.total ?? 0}`} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Llamadas por hora</h3>
          {cdrStats?.hourly?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={cdrStats.hourly} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="calls" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">
              Sin datos de llamadas
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Llamadas activas</h3>
          {channels.length === 0 ? (
            <div className="h-52 flex flex-col items-center justify-center text-gray-400">
              <PhoneCall size={40} className="mb-2 opacity-30" />
              <p className="text-sm">Sin llamadas activas</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-52 overflow-y-auto">
              {channels.map((ch, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm">
                  <div>
                    <p className="font-medium">{ch.caller?.number || ch.id}</p>
                    <p className="text-gray-400 text-xs">{ch.state}</p>
                  </div>
                  <span className="text-xs text-gray-400">{ch.dialplan?.context}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Asterisk info */}
      {status?.asterisk_info && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">Información del sistema</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-400">Versión</p>
              <p className="font-medium">{status.asterisk_info.build?.version || '—'}</p>
            </div>
            <div>
              <p className="text-gray-400">Sistema</p>
              <p className="font-medium">{status.asterisk_info.build?.os || '—'}</p>
            </div>
            <div>
              <p className="text-gray-400">AMI</p>
              <p className="font-medium">{status.ami_connected ? 'Conectado' : 'Desconectado'}</p>
            </div>
            <div>
              <p className="text-gray-400">ARI</p>
              <p className="font-medium">{status.ari_connected ? 'Conectado' : 'Desconectado'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
