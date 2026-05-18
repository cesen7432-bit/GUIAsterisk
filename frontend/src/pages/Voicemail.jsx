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

function VMForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({
    defaultValues: initial || { password: '1234', attach_audio: true }
  })
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Extensión" required>
          <input className="input" {...register('extension', { required: !initial })} readOnly={!!initial} />
        </FormField>
        <FormField label="PIN del buzón">
          <input className="input" {...register('password')} placeholder="1234" />
        </FormField>
        <FormField label="Email de notificación" className="col-span-2">
          <input className="input" type="email" {...register('email')} placeholder="usuario@empresa.com" />
        </FormField>
      </div>
      <div className="flex gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('attach_audio')} className="rounded" />
          Adjuntar audio en email
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('delete_after_email')} className="rounded" />
          Eliminar después de enviar email
        </label>
      </div>
      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </form>
  )
}

export default function Voicemail() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: vms = [], isLoading } = useQuery({
    queryKey: ['voicemail'],
    queryFn: () => api.get('/voicemail/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/voicemail/', d),
    onSuccess: () => { toast.success('Buzón creado'); qc.invalidateQueries(['voicemail']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/voicemail/${id}`, data),
    onSuccess: () => { toast.success('Buzón actualizado'); qc.invalidateQueries(['voicemail']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/voicemail/${id}`),
    onSuccess: () => { toast.success('Buzón eliminado'); qc.invalidateQueries(['voicemail']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Buzón de Voz</h1>
          <p className="text-gray-500 text-sm">{vms.length} buzones configurados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo buzón</button>
      </div>

      <Table headers={['Extensión', 'Email', 'Audio adjunto', 'Eliminar tras email', 'Acciones']} loading={isLoading}>
        {vms.map(v => (
          <Tr key={v.id}>
            <Td><span className="font-mono font-bold text-blue-700">{v.extension}</span></Td>
            <Td>{v.email || <span className="text-gray-300">—</span>}</Td>
            <Td><Badge variant={v.attach_audio ? 'green' : 'gray'}>{v.attach_audio ? 'Sí' : 'No'}</Badge></Td>
            <Td><Badge variant={v.delete_after_email ? 'red' : 'gray'}>{v.delete_after_email ? 'Sí' : 'No'}</Badge></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: v })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar buzón?')) deleteMut.mutate(v.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo buzón de voz">
        <VMForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar buzón: ${modal?.edit?.extension}`}>
        {modal?.edit && <VMForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
