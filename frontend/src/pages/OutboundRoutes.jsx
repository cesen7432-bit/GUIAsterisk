import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, ArrowUp, ArrowDown } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

function RouteForm({ initial, trunks, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({
    defaultValues: initial || { priority: 1, prefix_remove: 0, prefix_add: '' }
  })
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} placeholder="Salida_Local" />
        </FormField>
        <FormField label="Patrón de marcación" required>
          <input className="input" {...register('pattern', { required: true })} placeholder="_09XXXXXXXX" />
        </FormField>
        <FormField label="Trunk" required>
          <select className="input" {...register('trunk_id', { required: true, valueAsNumber: true })}>
            <option value="">Seleccionar...</option>
            {trunks.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </FormField>
        <FormField label="Prioridad">
          <input className="input" type="number" {...register('priority', { valueAsNumber: true })} />
        </FormField>
        <FormField label="Prefijo a agregar">
          <input className="input" {...register('prefix_add')} placeholder="ej: 9" />
        </FormField>
        <FormField label="Dígitos a quitar">
          <input className="input" type="number" {...register('prefix_remove', { valueAsNumber: true })} />
        </FormField>
      </div>
      <label className="flex items-center gap-2 cursor-pointer text-sm">
        <input type="checkbox" {...register('recording')} className="rounded" />
        Grabar llamadas en esta ruta
      </label>
      <div className="flex justify-end gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </form>
  )
}

export default function OutboundRoutes() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: routes = [], isLoading } = useQuery({
    queryKey: ['outbound-routes'],
    queryFn: () => api.get('/routes/outbound').then(r => r.data),
  })

  const { data: trunks = [] } = useQuery({
    queryKey: ['trunks'],
    queryFn: () => api.get('/trunks/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/routes/outbound', d),
    onSuccess: () => { toast.success('Ruta creada'); qc.invalidateQueries(['outbound-routes']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/routes/outbound/${id}`, data),
    onSuccess: () => { toast.success('Ruta actualizada'); qc.invalidateQueries(['outbound-routes']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/routes/outbound/${id}`),
    onSuccess: () => { toast.success('Ruta eliminada'); qc.invalidateQueries(['outbound-routes']) },
  })

  const trunkName = (id) => trunks.find(t => t.id === id)?.name || id

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rutas de Salida</h1>
          <p className="text-gray-500 text-sm">{routes.length} rutas configuradas</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nueva ruta</button>
      </div>

      <Table headers={['Nombre', 'Patrón', 'Trunk', 'Prefijo', 'Grabación', 'Prioridad', 'Acciones']} loading={isLoading}>
        {routes.map(r => (
          <Tr key={r.id}>
            <Td><span className="font-medium">{r.name}</span></Td>
            <Td><span className="font-mono text-sm">{r.pattern}</span></Td>
            <Td><Badge variant="purple">{trunkName(r.trunk_id)}</Badge></Td>
            <Td>
              {r.prefix_add && <span className="text-green-600 text-xs">+{r.prefix_add}</span>}
              {r.prefix_remove > 0 && <span className="text-red-500 text-xs ml-1">-{r.prefix_remove}</span>}
            </Td>
            <Td><Badge variant={r.recording ? 'red' : 'gray'}>{r.recording ? 'Sí' : 'No'}</Badge></Td>
            <Td>{r.priority}</Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: r })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(r.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva ruta de salida" size="lg">
        <RouteForm trunks={trunks} onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && <RouteForm initial={modal.edit} trunks={trunks} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
