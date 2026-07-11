import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, Eye } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

const VOICES = [
  { value: 'alloy',   label: 'Alloy (neutro)' },
  { value: 'ash',     label: 'Ash' },
  { value: 'coral',   label: 'Coral (femenino)' },
  { value: 'echo',    label: 'Echo (masculino)' },
  { value: 'sage',    label: 'Sage' },
  { value: 'shimmer', label: 'Shimmer (femenino)' },
  { value: 'verse',   label: 'Verse' },
]

const HINT = `Usa {{variable}} para datos dinámicos.
Ejemplo: Hola {{nombre}}, tienes un saldo de ${{monto}} pendiente.

Variables disponibles dependen de las columnas de tu CSV.`

function TemplateForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, watch } = useForm({
    defaultValues: initial || {
      name: '',
      system_prompt: '',
      first_message: '',
      voice: 'alloy',
      vad_threshold: 0.6,
    },
  })

  const sysPrompt = watch('system_prompt', '')
  const firstMsg  = watch('first_message', '')

  // Detectar variables usadas
  const vars = [...new Set([
    ...[...sysPrompt.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]),
    ...[...firstMsg.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]),
  ])]

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre de la plantilla" required>
          <input className="input" {...register('name', { required: true })} placeholder="cobranzas_v1" />
        </FormField>
        <FormField label="Voz">
          <select className="input" {...register('voice')}>
            {VOICES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
        </FormField>
      </div>

      <FormField label="Primer mensaje (lo que dice la IA al contestar)" required>
        <input
          className="input"
          {...register('first_message', { required: true })}
          placeholder="Hola, buenos días. ¿Hablo con {{nombre}}?"
        />
      </FormField>

      <FormField label="Instrucciones del sistema (system prompt)" required>
        <textarea
          className="input font-mono text-xs"
          rows={12}
          {...register('system_prompt', { required: true })}
          placeholder={HINT}
        />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Sensibilidad VAD (0.1–1.0)" hint="Mayor valor = menos sensible al ruido de fondo">
          <input
            className="input"
            type="number" step="0.1" min="0.1" max="1.0"
            {...register('vad_threshold', { valueAsNumber: true })}
          />
        </FormField>
        {vars.length > 0 && (
          <FormField label="Variables detectadas">
            <div className="flex flex-wrap gap-1 pt-1">
              {vars.map(v => (
                <span key={v} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-mono">
                  {`{{${v}}}`}
                </span>
              ))}
            </div>
          </FormField>
        )}
      </div>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar plantilla'}
        </button>
      </div>
    </form>
  )
}

function PreviewModal({ template, onClose }) {
  return (
    <Modal open={!!template} onClose={onClose} title={`Vista previa: ${template?.name}`} size="lg">
      {template && (
        <div className="space-y-4 text-sm">
          <div>
            <p className="label">Primer mensaje</p>
            <p className="bg-blue-50 text-blue-800 rounded p-3 font-medium">{template.first_message}</p>
          </div>
          <div>
            <p className="label">Voz: <span className="font-mono text-gray-700">{template.voice}</span>
              {' · '}VAD: <span className="font-mono text-gray-700">{template.vad_threshold}</span>
            </p>
          </div>
          <div>
            <p className="label">System prompt</p>
            <pre className="bg-gray-50 rounded p-3 text-xs overflow-auto max-h-64 whitespace-pre-wrap">
              {template.system_prompt}
            </pre>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default function VoiceTemplates() {
  const [modal, setModal]     = useState(null) // null | 'create' | {edit} | {preview}
  const qc = useQueryClient()

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['voice-templates'],
    queryFn: () => api.get('/campaigns/templates/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: d => api.post('/campaigns/templates/', d),
    onSuccess: () => { toast.success('Plantilla creada'); qc.invalidateQueries(['voice-templates']); setModal(null) },
    onError: e => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/campaigns/templates/${id}`, data),
    onSuccess: () => { toast.success('Plantilla actualizada'); qc.invalidateQueries(['voice-templates']); setModal(null) },
    onError: e => toast.error(e.response?.data?.detail || 'Error'),
  })

  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/campaigns/templates/${id}`),
    onSuccess: () => { toast.success('Plantilla eliminada'); qc.invalidateQueries(['voice-templates']) },
    onError: e => toast.error(e.response?.data?.detail || 'Error al eliminar'),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plantillas de voz IA</h1>
          <p className="text-gray-500 text-sm">{templates.length} plantillas — definen el comportamiento del agente</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}>
          <Plus size={16} /> Nueva plantilla
        </button>
      </div>

      <Table headers={['Nombre', 'Primer mensaje', 'Voz', 'VAD', 'Variables', 'Acciones']} loading={isLoading}>
        {templates.map(t => {
          const vars = [...new Set([
            ...[...t.system_prompt.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]),
            ...[...t.first_message.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]),
          ])]
          return (
            <Tr key={t.id}>
              <Td><span className="font-medium text-gray-900">{t.name}</span></Td>
              <Td><span className="text-gray-600 text-sm truncate max-w-xs block">{t.first_message}</span></Td>
              <Td><span className="font-mono text-xs">{t.voice}</span></Td>
              <Td><span className="font-mono text-xs">{t.vad_threshold}</span></Td>
              <Td>
                <div className="flex flex-wrap gap-1">
                  {vars.slice(0, 4).map(v => (
                    <span key={v} className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-xs font-mono">{`{{${v}}}`}</span>
                  ))}
                  {vars.length > 4 && <span className="text-xs text-gray-400">+{vars.length - 4}</span>}
                </div>
              </Td>
              <Td>
                <div className="flex gap-2">
                  <button onClick={() => setModal({ preview: t })} className="p-1.5 rounded hover:bg-gray-100 text-gray-500" title="Vista previa">
                    <Eye size={14} />
                  </button>
                  <button onClick={() => setModal({ edit: t })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600" title="Editar">
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => { if (confirm(`¿Eliminar plantilla "${t.name}"?`)) deleteMut.mutate(t.id) }}
                    className="p-1.5 rounded hover:bg-red-50 text-red-500" title="Eliminar"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </Td>
            </Tr>
          )
        })}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva plantilla de voz" size="lg">
        <TemplateForm onSubmit={d => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>

      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && (
          <TemplateForm
            initial={modal.edit}
            onSubmit={d => updateMut.mutate({ id: modal.edit.id, data: d })}
            loading={updateMut.isPending}
          />
        )}
      </Modal>

      <PreviewModal template={modal?.preview} onClose={() => setModal(null)} />
    </div>
  )
}
