import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

const DEST_TYPES = ['extension','queue','ivr','voicemail','hangup']

function RouteForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({ defaultValues: initial || { destination_type: 'extension' } })
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="DID (vacío = cualquier número)">
          <input className="input" {...register('did')} placeholder="5551234567" />
        </FormField>
        <FormField label="CallerID (vacío = cualquier)">
          <input className="input" {...register('callerid')} />
        </FormField>
        <FormField label="Tipo de destino" required>
          <select className="input" {...register('destination_type')}>
            {DEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </FormField>
        <FormField label="ID de destino">
          <input className="input" {...register('destination_id')} placeholder="100, soporte, 1..." />
        </FormField>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </form>
  )
}

export default function InboundRoutes() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: routes = [], isLoading } = useQuery({
    queryKey: ['inbound-routes'],
    queryFn: () => api.get('/routes/inbound').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/routes/inbound', d),
    onSuccess: () => { toast.success('Ruta creada'); qc.invalidateQueries(['inbound-routes']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/routes/inbound/${id}`, data),
    onSuccess: () => { toast.success('Ruta actualizada'); qc.invalidateQueries(['inbound-routes']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/routes/inbound/${id}`),
    onSuccess: () => { toast.success('Ruta eliminada'); qc.invalidateQueries(['inbound-routes']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rutas de Entrada</h1>
          <p className="text-gray-500 text-sm">{routes.length} rutas configuradas</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nueva ruta</button>
      </div>

      <Table headers={['DID', 'CallerID', 'Destino', 'ID destino', 'Acciones']} loading={isLoading}>
        {routes.map(r => (
          <Tr key={r.id}>
            <Td><span className="font-mono">{r.did || <span className="text-gray-400 italic">cualquier</span>}</span></Td>
            <Td>{r.callerid || <span className="text-gray-300">—</span>}</Td>
            <Td><Badge variant="blue">{r.destination_type}</Badge></Td>
            <Td><span className="font-mono text-sm">{r.destination_id}</span></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: r })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(r.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva ruta de entrada">
        <RouteForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title="Editar ruta de entrada">
        {modal?.edit && <RouteForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
