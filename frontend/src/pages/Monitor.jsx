import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { PhoneOff, ArrowRight, Eye } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import toast from 'react-hot-toast'
import api from '../api/client'

function duration(secs) {
  const m = Math.floor(secs / 60), s = secs % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function Monitor() {
  const [events, setEvents] = useState([])
  const [transferModal, setTransferModal] = useState(null)
  const [transferTo, setTransferTo] = useState('')

  const { data: channels = [], refetch } = useQuery({
    queryKey: ['monitor-channels'],
    queryFn: () => api.get('/monitor/channels').then(r => r.data.channels || []),
    refetchInterval: 3000,
  })

  const { data: endpoints } = useQuery({
    queryKey: ['monitor-endpoints'],
    queryFn: () => api.get('/monitor/endpoints').then(r => r.data.endpoints || []),
    refetchInterval: 5000,
  })

  useWebSocket(useCallback((msg) => {
    if (msg.source === 'ari' || msg.source === 'ami') {
      setEvents(prev => [{ ...msg, ts: new Date().toLocaleTimeString() }, ...prev.slice(0, 49)])
      if (['StasisStart', 'StasisEnd', 'ChannelStateChange', 'Hangup', 'Newchannel'].includes(
        msg.event?.type || msg.event?.Event
      )) {
        refetch()
      }
    }
  }, [refetch]))

  const hangupMut = useMutation({
    mutationFn: (id) => api.post(`/monitor/channels/${id}/hangup`),
    onSuccess: () => { toast.success('Llamada colgada'); refetch() },
    onError: () => toast.error('Error al colgar'),
  })

  const transferMut = useMutation({
    mutationFn: ({ id, exten }) => api.post(`/monitor/channels/${id}/transfer?exten=${exten}`),
    onSuccess: () => { toast.success('Transferencia enviada'); setTransferModal(null) },
    onError: () => toast.error('Error en transferencia'),
  })

  const endpointState = (tech, resource) => {
    const ep = endpoints?.find(e => e.resource === resource || e.channel_ids?.includes(resource))
    return ep?.state || 'unknown'
  }

  const stateColor = (state) => {
    const map = { available: 'green', busy: 'red', ringing: 'yellow', unavailable: 'gray', unknown: 'gray' }
    return map[state] || 'gray'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Monitor en Tiempo Real</h1>
        <p className="text-gray-500 text-sm">{channels.length} canal(es) activo(s)</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Active channels */}
        <div className="xl:col-span-2 card">
          <h3 className="font-semibold text-gray-900 mb-4">Llamadas activas</h3>
          {channels.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">Sin llamadas activas</div>
          ) : (
            <div className="space-y-2">
              {channels.map((ch) => (
                <div key={ch.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex items-center gap-3">
                    <Badge variant={ch.state === 'Up' ? 'green' : 'yellow'} dot>{ch.state}</Badge>
                    <div>
                      <p className="text-sm font-medium">{ch.caller?.number || 'Desconocido'}</p>
                      <p className="text-xs text-gray-400">{ch.id?.substring(0, 40)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">{ch.dialplan?.context}</span>
                    <button onClick={() => setTransferModal(ch.id)} className="p-1.5 rounded hover:bg-blue-50 text-blue-600" title="Transferir">
                      <ArrowRight size={14} />
                    </button>
                    <button onClick={() => { if (confirm('¿Colgar?')) hangupMut.mutate(ch.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500" title="Colgar">
                      <PhoneOff size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live events */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Eventos en tiempo real</h3>
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {events.length === 0 && <p className="text-gray-400 text-sm">Esperando eventos...</p>}
            {events.map((ev, i) => (
              <div key={i} className="text-xs border-b border-gray-50 py-1">
                <span className="text-gray-400">{ev.ts} </span>
                <span className={`font-medium ${ev.source === 'ari' ? 'text-blue-600' : 'text-purple-600'}`}>
                  [{ev.source.toUpperCase()}]
                </span>
                <span className="text-gray-700 ml-1">
                  {ev.event?.type || ev.event?.Event || 'event'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal open={!!transferModal} onClose={() => setTransferModal(null)} title="Transferir llamada" size="sm">
        <div className="space-y-4">
          <div>
            <label className="label">Transferir a extensión</label>
            <input className="input" value={transferTo} onChange={e => setTransferTo(e.target.value)} placeholder="101" autoFocus />
          </div>
          <div className="flex justify-end gap-3">
            <button className="btn-secondary" onClick={() => setTransferModal(null)}>Cancelar</button>
            <button className="btn-primary" onClick={() => transferMut.mutate({ id: transferModal, exten: transferTo })}>
              Transferir
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
