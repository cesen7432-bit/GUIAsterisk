import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { useForm, useFieldArray } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

const DEST_TYPES = ['extension', 'queue', 'ivr', 'voicemail', 'hangup']
const KEYS = ['0','1','2','3','4','5','6','7','8','9','*','#']

function IVRForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, control } = useForm({
    defaultValues: initial || { timeout: 10, max_attempts: 3, invalid_action: 'repeat', timeout_action: 'repeat', options: [] }
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'options' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} placeholder="IVR Principal" />
        </FormField>
        <FormField label="Audio de bienvenida">
          <input className="input" {...register('welcome_audio')} placeholder="welcome" />
        </FormField>
        <FormField label="Timeout (s)">
          <input className="input" type="number" {...register('timeout')} />
        </FormField>
        <FormField label="Máx. intentos">
          <input className="input" type="number" {...register('max_attempts')} />
        </FormField>
        <FormField label="Acción inválida">
          <select className="input" {...register('invalid_action')}>
            <option value="repeat">Repetir menú</option>
            <option value="hangup">Colgar</option>
          </select>
        </FormField>
        <FormField label="Acción timeout">
          <select className="input" {...register('timeout_action')}>
            <option value="repeat">Repetir menú</option>
            <option value="hangup">Colgar</option>
          </select>
        </FormField>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Opciones DTMF</label>
          <button type="button" className="btn-secondary text-xs py-1" onClick={() => append({ key: '1', destination_type: 'extension', destination_id: '' })}>
            <Plus size={12} /> Agregar opción
          </button>
        </div>
        <div className="space-y-2">
          {fields.map((f, i) => (
            <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
              <select className="input col-span-2" {...register(`options.${i}.key`)}>
                {KEYS.map(k => <option key={k} value={k}>{k}</option>)}
              </select>
              <select className="input col-span-3" {...register(`options.${i}.destination_type`)}>
                {DEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input className="input col-span-6" {...register(`options.${i}.destination_id`)} placeholder="ID destino (ej: 100, soporte, 1)" />
              <button type="button" onClick={() => remove(i)} className="col-span-1 p-1.5 text-red-500 hover:bg-red-50 rounded">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </form>
  )
}

export default function IVR() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: ivrs = [], isLoading } = useQuery({
    queryKey: ['ivr'],
    queryFn: () => api.get('/ivr/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (data) => api.post('/ivr/', data),
    onSuccess: () => { toast.success('IVR creado'); qc.invalidateQueries(['ivr']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const loadIvr = async (ivr) => {
    const { data } = await api.get(`/ivr/${ivr.id}`)
    setModal({ edit: data })
  }

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/ivr/${id}`, data),
    onSuccess: () => { toast.success('IVR actualizado'); qc.invalidateQueries(['ivr']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/ivr/${id}`),
    onSuccess: () => { toast.success('IVR eliminado'); qc.invalidateQueries(['ivr']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">IVR (Menú de opciones)</h1>
          <p className="text-gray-500 text-sm">{ivrs.length} IVRs configurados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo IVR</button>
      </div>

      <Table headers={['Nombre', 'Audio', 'Timeout', 'Opciones', 'Acciones']} loading={isLoading}>
        {ivrs.map(ivr => (
          <Tr key={ivr.id}>
            <Td><span className="font-medium">{ivr.name}</span></Td>
            <Td><span className="font-mono text-xs text-gray-500">{ivr.welcome_audio || '—'}</span></Td>
            <Td>{ivr.timeout}s</Td>
            <Td>{ivr.options_count} opciones</Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => loadIvr(ivr)} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(ivr.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo IVR" size="lg">
        <IVRForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar IVR: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && <IVRForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
