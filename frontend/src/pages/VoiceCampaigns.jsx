import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Play, Pause, StopCircle, Upload, Eye,
  Edit2, Trash2, Users, FileText, RefreshCw,
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  draft:    'gray',
  active:   'green',
  paused:   'yellow',
  finished: 'blue',
}
const STATUS_LABELS = {
  draft: 'Borrador', active: 'Activa', paused: 'Pausada', finished: 'Finalizada',
}
const CONTACT_COLORS = {
  pending:   'gray',
  calling:   'blue',
  completed: 'green',
  voicemail: 'yellow',
  no_answer: 'red',
  failed:    'red',
}

const fmtDate = d => d ? new Date(d).toLocaleString('es-EC') : '—'
const fmtDur  = s => s != null ? `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}` : '—'

// ── Formulario de campaña ─────────────────────────────────────────────────────

function CampaignForm({ initial, templates, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({
    defaultValues: initial || {
      name: '',
      template_id: templates[0]?.id || '',
      max_concurrent: 4,
      schedule_start: '09:00',
      schedule_end:   '18:00',
      max_retries: 3,
      retry_delay_minutes: 120,
      trunk: 'openvox',
    },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre de la campaña" required>
          <input className="input" {...register('name', { required: true })} placeholder="Cobranzas Julio" />
        </FormField>
        <FormField label="Plantilla de voz" required>
          <select className="input" {...register('template_id', { required: true, valueAsNumber: true })}>
            <option value="">— seleccionar —</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </FormField>
        <FormField label="Llamadas simultáneas">
          <input className="input" type="number" min={1} max={16} {...register('max_concurrent', { valueAsNumber: true })} />
        </FormField>
        <FormField label="Troncal SIP">
          <input className="input" {...register('trunk')} placeholder="openvox" />
        </FormField>
        <FormField label="Horario inicio">
          <input className="input" type="time" {...register('schedule_start')} />
        </FormField>
        <FormField label="Horario fin">
          <input className="input" type="time" {...register('schedule_end')} />
        </FormField>
        <FormField label="Máx. reintentos">
          <input className="input" type="number" min={0} max={10} {...register('max_retries', { valueAsNumber: true })} />
        </FormField>
        <FormField label="Espera entre reintentos (min)">
          <input className="input" type="number" min={5} {...register('retry_delay_minutes', { valueAsNumber: true })} />
        </FormField>
      </div>
      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar campaña'}
        </button>
      </div>
    </form>
  )
}

// ── Detalle de campaña (contactos + logs) ─────────────────────────────────────

function CampaignDetail({ campaign, onClose }) {
  const [tab, setTab] = useState('contacts')
  const [statusFilter, setStatusFilter] = useState('')
  const fileRef = useRef()
  const qc = useQueryClient()

  const { data: contactsData, isLoading: loadingContacts } = useQuery({
    queryKey: ['campaign-contacts', campaign.id, statusFilter],
    queryFn: () => {
      const params = statusFilter ? `?status=${statusFilter}` : ''
      return api.get(`/campaigns/${campaign.id}/contacts${params}`).then(r => r.data)
    },
    enabled: tab === 'contacts',
  })

  const { data: logs = [], isLoading: loadingLogs } = useQuery({
    queryKey: ['campaign-logs', campaign.id],
    queryFn: () => api.get(`/campaigns/${campaign.id}/logs`).then(r => r.data),
    enabled: tab === 'logs',
  })

  const uploadMut = useMutation({
    mutationFn: async (file) => {
      const form = new FormData()
      form.append('file', file)
      return api.post(`/campaigns/${campaign.id}/contacts/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: r => {
      toast.success(`${r.data.added} contactos importados`)
      qc.invalidateQueries(['campaign-contacts', campaign.id])
      qc.invalidateQueries(['voice-campaigns'])
    },
    onError: e => toast.error(e.response?.data?.detail || 'Error al importar CSV'),
  })

  const resetMut = useMutation({
    mutationFn: () => api.delete(`/campaigns/${campaign.id}/contacts`),
    onSuccess: () => {
      toast.success('Contactos reiniciados a pendiente')
      qc.invalidateQueries(['campaign-contacts', campaign.id])
      qc.invalidateQueries(['voice-campaigns'])
    },
  })

  const contacts = contactsData?.items || []
  const total    = contactsData?.total ?? 0

  const STATUSES = ['', 'pending', 'calling', 'completed', 'voicemail', 'no_answer', 'failed']

  return (
    <Modal open onClose={onClose} title={`Campaña: ${campaign.name}`} size="xl">
      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {[['contacts', Users, 'Contactos'], ['logs', FileText, 'Registros de llamadas']].map(([key, Icon, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Contactos */}
      {tab === 'contacts' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex gap-2 items-center">
              <select
                className="input py-1.5 text-sm w-40"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                {STATUSES.map(s => (
                  <option key={s} value={s}>{s || `Todos (${total})`}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                className="btn-secondary text-xs py-1.5"
                onClick={() => { if (confirm('¿Reiniciar todos a pendiente?')) resetMut.mutate() }}
                disabled={resetMut.isPending}
              >
                <RefreshCw size={12} /> Reiniciar
              </button>
              <input
                type="file" accept=".csv" ref={fileRef} className="hidden"
                onChange={e => { if (e.target.files[0]) uploadMut.mutate(e.target.files[0]); e.target.value = '' }}
              />
              <button
                className="btn-primary text-xs py-1.5"
                onClick={() => fileRef.current?.click()}
                disabled={uploadMut.isPending}
              >
                <Upload size={12} /> {uploadMut.isPending ? 'Importando...' : 'Importar CSV'}
              </button>
            </div>
          </div>

          {/* Hint CSV */}
          <p className="text-xs text-gray-400">
            El CSV debe tener columna <code className="bg-gray-100 px-1 rounded">phone</code>.
            El resto de columnas son variables de la plantilla (ej: nombre, monto, fecha_vencimiento).
          </p>

          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  {['Teléfono', 'Variables', 'Estado', 'Intentos', 'Resultado', 'Actualizado'].map(h => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loadingContacts ? (
                  <tr><td colSpan={6} className="py-8 text-center text-gray-400">Cargando...</td></tr>
                ) : contacts.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <Td><span className="font-mono">{c.phone}</span></Td>
                    <Td>
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {Object.entries(c.variables || {}).slice(0, 3).map(([k, v]) => (
                          <span key={k} className="text-xs text-gray-500">
                            <span className="font-medium">{k}:</span> {String(v).slice(0, 20)}
                          </span>
                        ))}
                      </div>
                    </Td>
                    <Td><Badge variant={CONTACT_COLORS[c.status] || 'gray'}>{c.status}</Badge></Td>
                    <Td>{c.attempts}</Td>
                    <Td>
                      {c.result?.resumen
                        ? <span className="text-xs text-gray-600 max-w-xs block truncate">{c.result.resumen}</span>
                        : <span className="text-gray-300">—</span>}
                    </Td>
                    <Td><span className="text-xs text-gray-400">{fmtDate(c.updated_at)}</span></Td>
                  </tr>
                ))}
                {!loadingContacts && contacts.length === 0 && (
                  <tr><td colSpan={6} className="py-8 text-center text-gray-400">Sin contactos. Importa un CSV.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Logs */}
      {tab === 'logs' && (
        <div className="overflow-auto max-h-[32rem]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left">
                {['Teléfono (contacto)', 'Inicio', 'Duración', 'Resultado', 'Transcripción', 'Resumen IA'].map(h => (
                  <th key={h} className="pb-2 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loadingLogs ? (
                <tr><td colSpan={6} className="py-8 text-center text-gray-400">Cargando...</td></tr>
              ) : logs.map(log => (
                <tr key={log.id} className="hover:bg-gray-50 align-top">
                  <Td><span className="font-mono text-xs">{log.contact_id}</span></Td>
                  <Td><span className="text-xs">{fmtDate(log.started_at)}</span></Td>
                  <Td><span className="font-mono text-xs">{fmtDur(log.duration_seconds)}</span></Td>
                  <Td>
                    <Badge variant={
                      log.disposition === 'completado' ? 'green'
                      : log.disposition === 'voicemail' ? 'yellow'
                      : log.disposition === 'no_answer' ? 'red'
                      : 'gray'
                    }>{log.disposition || '—'}</Badge>
                  </Td>
                  <Td>
                    {log.transcript
                      ? <details className="text-xs text-gray-600 max-w-xs">
                          <summary className="cursor-pointer text-blue-600 hover:underline">Ver ({log.transcript.length} car.)</summary>
                          <pre className="mt-1 bg-gray-50 rounded p-2 whitespace-pre-wrap max-h-40 overflow-auto">{log.transcript}</pre>
                        </details>
                      : <span className="text-gray-300">—</span>}
                  </Td>
                  <Td>
                    {log.summary?.resumen
                      ? <span className="text-xs text-gray-600 block max-w-xs">{log.summary.resumen}</span>
                      : <span className="text-gray-300">—</span>}
                  </Td>
                </tr>
              ))}
              {!loadingLogs && logs.length === 0 && (
                <tr><td colSpan={6} className="py-8 text-center text-gray-400">Sin llamadas registradas aún.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  )
}

// ── Página principal ───────────────────────────────────────────────────────────

export default function VoiceCampaigns() {
  const [modal, setModal]     = useState(null) // null | 'create' | {edit} | {detail}
  const qc = useQueryClient()

  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['voice-campaigns'],
    queryFn: () => api.get('/campaigns/').then(r => r.data),
    refetchInterval: 8000,
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['voice-templates'],
    queryFn: () => api.get('/campaigns/templates/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: d => api.post('/campaigns/', d),
    onSuccess: () => { toast.success('Campaña creada'); qc.invalidateQueries(['voice-campaigns']); setModal(null) },
    onError: e => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/campaigns/${id}`, data),
    onSuccess: () => { qc.invalidateQueries(['voice-campaigns']); setModal(null) },
    onError: e => toast.error(e.response?.data?.detail || 'Error'),
  })

  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/campaigns/${id}`),
    onSuccess: () => { toast.success('Campaña eliminada'); qc.invalidateQueries(['voice-campaigns']) },
  })

  const setStatus = (id, status) =>
    updateMut.mutate({ id, data: { status } }, {
      onSuccess: () => toast.success(`Campaña ${STATUS_LABELS[status].toLowerCase()}`),
    })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campañas de voz IA</h1>
          <p className="text-gray-500 text-sm">{campaigns.length} campañas — marcador automático con IA conversacional</p>
        </div>
        <button
          className="btn-primary"
          onClick={() => {
            if (templates.length === 0) {
              toast.error('Crea una plantilla de voz primero')
              return
            }
            setModal('create')
          }}
        >
          <Plus size={16} /> Nueva campaña
        </button>
      </div>

      {/* Cards de campañas */}
      {!isLoading && campaigns.length === 0 && (
        <div className="card text-center py-12 text-gray-400">
          <p className="text-lg font-medium">Sin campañas</p>
          <p className="text-sm mt-1">Crea una plantilla de voz y luego una campaña para empezar.</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {campaigns.map(c => {
          const tpl = templates.find(t => t.id === c.template_id)
          const { total, pending, calling, completed } = c.stats || {}
          const pct = total > 0 ? Math.round((completed / total) * 100) : 0
          return (
            <div key={c.id} className="card space-y-3">
              {/* Encabezado */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{c.name}</h3>
                    <Badge variant={STATUS_COLORS[c.status]}>{STATUS_LABELS[c.status]}</Badge>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Plantilla: <span className="font-medium text-gray-600">{tpl?.name || c.template_id}</span>
                    {' · '}Troncal: <span className="font-mono">{c.trunk}</span>
                    {' · '}Horario: {c.schedule_start?.slice(0,5)}–{c.schedule_end?.slice(0,5)}
                    {' · '}Max simultáneas: {c.max_concurrent}
                  </p>
                </div>
                {/* Acciones de estado */}
                <div className="flex gap-2 shrink-0">
                  {c.status !== 'active' && c.status !== 'finished' && (
                    <button
                      onClick={() => setStatus(c.id, 'active')}
                      className="btn-primary text-xs py-1.5 bg-green-600 hover:bg-green-700"
                      title="Activar campaña"
                    >
                      <Play size={12} /> Activar
                    </button>
                  )}
                  {c.status === 'active' && (
                    <button
                      onClick={() => setStatus(c.id, 'paused')}
                      className="btn-secondary text-xs py-1.5"
                      title="Pausar campaña"
                    >
                      <Pause size={12} /> Pausar
                    </button>
                  )}
                  {c.status !== 'finished' && (
                    <button
                      onClick={() => { if (confirm('¿Marcar como finalizada?')) setStatus(c.id, 'finished') }}
                      className="btn-secondary text-xs py-1.5"
                      title="Finalizar"
                    >
                      <StopCircle size={12} />
                    </button>
                  )}
                  <button
                    onClick={() => setModal({ detail: c })}
                    className="btn-secondary text-xs py-1.5"
                    title="Ver contactos y llamadas"
                  >
                    <Eye size={12} /> Detalle
                  </button>
                  <button
                    onClick={() => setModal({ edit: c })}
                    className="p-1.5 rounded hover:bg-blue-50 text-blue-600"
                    title="Editar"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => { if (confirm(`¿Eliminar campaña "${c.name}"?`)) deleteMut.mutate(c.id) }}
                    className="p-1.5 rounded hover:bg-red-50 text-red-500"
                    title="Eliminar"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Barra de progreso + stats */}
              {total > 0 && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{completed}/{total} completados ({pct}%)</span>
                    <span className="flex gap-3">
                      {calling > 0 && <span className="text-blue-600 font-medium">{calling} en llamada</span>}
                      {pending > 0 && <span className="text-gray-500">{pending} pendientes</span>}
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )}
              {total === 0 && (
                <p className="text-xs text-yellow-600 bg-yellow-50 rounded px-3 py-1.5">
                  Sin contactos — importa un CSV con el botón <strong>Detalle → Importar CSV</strong>
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Modales */}
      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva campaña" size="lg">
        <CampaignForm
          templates={templates}
          onSubmit={d => createMut.mutate(d)}
          loading={createMut.isPending}
        />
      </Modal>

      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && (
          <CampaignForm
            initial={modal.edit}
            templates={templates}
            onSubmit={d => updateMut.mutate({ id: modal.edit.id, data: d })}
            loading={updateMut.isPending}
          />
        )}
      </Modal>

      {modal?.detail && (
        <CampaignDetail campaign={modal.detail} onClose={() => setModal(null)} />
      )}
    </div>
  )
}
