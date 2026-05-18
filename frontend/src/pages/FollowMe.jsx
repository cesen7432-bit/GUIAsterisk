import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { useForm, useFieldArray } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

function FMForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, control } = useForm({
    defaultValues: initial || { initial_ring_time: 20, strategy: 'sequential', music_on_hold: 'default', destinations: [] }
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'destinations' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Extensión base" required>
          <input className="input" {...register('extension', { required: !initial })} readOnly={!!initial} placeholder="100" />
        </FormField>
        <FormField label="Tiempo ring principal (s)">
          <input className="input" type="number" {...register('initial_ring_time')} />
        </FormField>
        <FormField label="Estrategia">
          <select className="input" {...register('strategy')}>
            <option value="sequential">Secuencial</option>
            <option value="simultaneous">Simultáneo</option>
          </select>
        </FormField>
        <FormField label="Música en espera">
          <input className="input" {...register('music_on_hold')} />
        </FormField>
      </div>
      <div className="flex gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('is_active')} className="rounded" />
          Activar sígueme
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('confirm_calls')} className="rounded" />
          Confirmar llamada
        </label>
      </div>
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Destinos secundarios</label>
          <button type="button" className="btn-secondary text-xs py-1" onClick={() => append({ number: '', timeout: 20, order: fields.length + 1 })}>
            <Plus size={12} /> Agregar
          </button>
        </div>
        <div className="space-y-2">
          {fields.map((f, i) => (
            <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
              <input className="input col-span-6" {...register(`destinations.${i}.number`)} placeholder="Número o extensión" />
              <input className="input col-span-3" type="number" {...register(`destinations.${i}.timeout`)} placeholder="Timeout" />
              <input className="input col-span-2" type="number" {...register(`destinations.${i}.order`)} placeholder="Orden" />
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

export default function FollowMe() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: fms = [], isLoading } = useQuery({
    queryKey: ['followme'],
    queryFn: () => api.get('/followme/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/followme/', d),
    onSuccess: () => { toast.success('Follow Me creado'); qc.invalidateQueries(['followme']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const loadFm = async (fm) => {
    const { data } = await api.get(`/followme/${fm.extension}`)
    setModal({ edit: data })
  }

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/followme/${id}`, data),
    onSuccess: () => { toast.success('Actualizado'); qc.invalidateQueries(['followme']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/followme/${id}`),
    onSuccess: () => { toast.success('Eliminado'); qc.invalidateQueries(['followme']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sígueme (Follow Me)</h1>
          <p className="text-gray-500 text-sm">{fms.length} configuraciones</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo</button>
      </div>

      <Table headers={['Extensión', 'Estado', 'Estrategia', 'Destinos', 'Acciones']} loading={isLoading}>
        {fms.map(fm => (
          <Tr key={fm.id}>
            <Td><span className="font-mono font-bold text-blue-700">{fm.extension}</span></Td>
            <Td><Badge variant={fm.is_active ? 'green' : 'gray'}>{fm.is_active ? 'Activo' : 'Inactivo'}</Badge></Td>
            <Td>{fm.strategy}</Td>
            <Td>{fm.destinations_count} destinos</Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => loadFm(fm)} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(fm.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo Follow Me" size="lg">
        <FMForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar Follow Me: ${modal?.edit?.extension}`} size="lg">
        {modal?.edit && <FMForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
