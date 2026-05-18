import { useMutation, useQuery } from '@tanstack/react-query'
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/client'

export default function SystemConfig() {
  const { data: status, refetch } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get('/system/status').then(r => r.data),
    refetchInterval: 10000,
  })

  const reloadMut = useMutation({
    mutationFn: (module) => api.post(`/system/reload${module ? `?module=${module}` : ''}`),
    onSuccess: () => toast.success('Reload enviado a Asterisk'),
    onError: () => toast.error('Error al recargar'),
  })

  const genMut = useMutation({
    mutationFn: () => api.post('/system/generate-configs'),
    onSuccess: () => toast.success('Configuraciones generadas y aplicadas'),
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const modules = [
    { label: 'PJSIP', module: 'res_pjsip.so' },
    { label: 'Dialplan', module: 'pbx_config.so' },
    { label: 'Colas', module: 'app_queue.so' },
    { label: 'Voicemail', module: 'app_voicemail.so' },
    { label: 'FollowMe', module: 'app_followme.so' },
    { label: 'ARI', module: 'res_ari.so' },
    { label: 'Todo Asterisk', module: '' },
  ]

  const info = status?.asterisk_info

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configuración del Sistema</h1>
        <p className="text-gray-500 text-sm">Estado y controles de Asterisk</p>
      </div>

      {/* Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'AMI', ok: status?.ami_connected },
          { label: 'ARI', ok: status?.ari_connected },
        ].map(({ label, ok }) => (
          <div key={label} className="card flex items-center gap-3">
            {ok
              ? <CheckCircle size={20} className="text-green-500" />
              : <AlertCircle size={20} className="text-red-400" />}
            <div>
              <p className="font-semibold text-sm">{label}</p>
              <p className="text-xs text-gray-500">{ok ? 'Conectado' : 'Desconectado'}</p>
            </div>
          </div>
        ))}
      </div>

      {info && (
        <div className="card">
          <h3 className="font-semibold mb-3">Información de Asterisk</h3>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {[
              ['Versión', info.build?.version],
              ['SO', info.build?.os],
              ['Arch', info.build?.machine],
              ['Usuario', info.build?.user],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-gray-400">{k}</dt>
                <dd className="font-medium">{v || '—'}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Reload modules */}
      <div className="card">
        <h3 className="font-semibold mb-4">Recargar módulos</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {modules.map(({ label, module }) => (
            <button
              key={label}
              onClick={() => reloadMut.mutate(module)}
              disabled={reloadMut.isPending}
              className="btn-secondary justify-center"
            >
              <RefreshCw size={14} /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* Generate configs */}
      <div className="card">
        <h3 className="font-semibold mb-2">Regenerar configuraciones</h3>
        <p className="text-sm text-gray-500 mb-4">
          Regenera todos los archivos .conf desde la base de datos y recarga los módulos correspondientes.
          Se hace backup automático antes de cada cambio.
        </p>
        <button
          onClick={() => genMut.mutate()}
          disabled={genMut.isPending}
          className="btn-primary"
        >
          <RefreshCw size={14} />
          {genMut.isPending ? 'Generando...' : 'Generar y aplicar todas las configuraciones'}
        </button>
      </div>

      {/* Config path info */}
      <div className="card bg-gray-50 border-gray-200">
        <h3 className="font-semibold mb-3 text-sm">Archivos gestionados</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs font-mono text-gray-600">
          {['pjsip.conf', 'extensions.conf', 'queues.conf', 'voicemail.conf', 'followme.conf', 'ari.conf'].map(f => (
            <div key={f} className="bg-white px-3 py-2 rounded-lg border border-gray-200">/etc/asterisk/{f}</div>
          ))}
        </div>
      </div>
    </div>
  )
}
