import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, Activity, Pause, Play } from 'lucide-react'
import { useForm, useFieldArray } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

function QueueForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, control } = useForm({
    defaultValues: initial || { strategy: 'ringall', agent_timeout: 30, retry: 5,
      wrapup_time: 5, max_callers: 0, music_on_hold: 'default',
      announce_frequency: 30, members: [] }
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'members' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} placeholder="soporte" />
        </FormField>
        <FormField label="Estrategia">
          <select className="input" {...register('strategy')}>
            {['ringall','roundrobin','leastrecent','fewestcalls','random'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Timeout agente (s)">
          <input className="input" type="number" {...register('agent_timeout')} />
        </FormField>
        <FormField label="Reintento (s)">
          <input className="input" type="number" {...register('retry')} />
        </FormField>
        <FormField label="Wrap-up (s)">
          <input className="input" type="number" {...register('wrapup_time')} />
        </FormField>
        <FormField label="Máx. en cola (0=ilimitado)">
          <input className="input" type="number" {...register('max_callers')} />
        </FormField>
        <FormField label="Música en espera">
          <input className="input" {...register('music_on_hold')} />
        </FormField>
      </div>
      <div className="flex gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('announce_position')} className="rounded" />
          Anunciar posición
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('announce_hold_time')} className="rounded" />
          Anunciar tiempo espera
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('recording')} className="rounded" />
          Grabar llamadas
        </label>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Agentes miembros</label>
          <button type="button" className="btn-secondary text-xs py-1" onClick={() => append({ extension: '', penalty: 0 })}>
            <Plus size={12} /> Agregar
          </button>
        </div>
        <div className="space-y-2">
          {fields.map((f, i) => (
            <div key={f.id} className="flex gap-2 items-center">
              <input className="input flex-1" {...register(`members.${i}.extension`)} placeholder="Extensión (ej: 100)" />
              <input className="input w-24" type="number" {...register(`members.${i}.penalty`)} placeholder="Penalidad" />
              <button type="button" onClick={() => remove(i)} className="p-1.5 text-red-500 hover:bg-red-50 rounded">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </form>
  )
}

export default function Queues() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: queues = [], isLoading } = useQuery({
    queryKey: ['queues'],
    queryFn: () => api.get('/queues/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (data) => api.post('/queues/', data),
    onSuccess: () => { toast.success('Cola creada'); qc.invalidateQueries(['queues']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const loadQueue = async (q) => {
    const { data } = await api.get(`/queues/${q.id}`)
    setModal({ edit: data })
  }

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/queues/${id}`, data),
    onSuccess: () => { toast.success('Cola actualizada'); qc.invalidateQueries(['queues']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/queues/${id}`),
    onSuccess: () => { toast.success('Cola eliminada'); qc.invalidateQueries(['queues']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Colas (Queues)</h1>
          <p className="text-gray-500 text-sm">{queues.length} colas configuradas</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}>
          <Plus size={16} /> Nueva cola
        </button>
      </div>

      <Table headers={['Nombre', 'Estrategia', 'Agentes', 'Grabación', 'Acciones']} loading={isLoading}>
        {queues.map(q => (
          <Tr key={q.id}>
            <Td><span className="font-medium">{q.name}</span></Td>
            <Td><Badge variant="blue">{q.strategy}</Badge></Td>
            <Td>{q.members_count} agentes</Td>
            <Td><Badge variant={q.recording ? 'red' : 'gray'}>{q.recording ? 'Activa' : 'No'}</Badge></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => loadQueue(q)} className="p-1.5 rounded hover:bg-blue-50 text-blue-600">
                  <Edit2 size={14} />
                </button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(q.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500">
                  <Trash2 size={14} />
                </button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva cola" size="lg">
        <QueueForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar cola: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && <QueueForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
