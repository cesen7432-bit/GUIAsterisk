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

const ROLE_COLORS = { admin: 'red', supervisor: 'yellow', agent: 'blue' }

function UserForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({ defaultValues: initial || { role: 'agent', is_active: true } })
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} />
        </FormField>
        <FormField label="Email" required>
          <input className="input" type="email" {...register('email', { required: true })} />
        </FormField>
        <FormField label={initial ? 'Nueva contraseña (vacío = sin cambio)' : 'Contraseña'}>
          <input className="input" type="password" {...register('password', { required: !initial })} />
        </FormField>
        <FormField label="Rol">
          <select className="input" {...register('role')}>
            <option value="admin">Admin</option>
            <option value="supervisor">Supervisor</option>
            <option value="agent">Agente</option>
          </select>
        </FormField>
        <FormField label="Extensión asignada">
          <input className="input" {...register('extension')} placeholder="100" />
        </FormField>
      </div>
      <label className="flex items-center gap-2 cursor-pointer text-sm">
        <input type="checkbox" {...register('is_active')} className="rounded" />
        Usuario activo
      </label>
      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </form>
  )
}

export default function GUIUsers() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['gui-users'],
    queryFn: () => api.get('/users/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/users/', d),
    onSuccess: () => { toast.success('Usuario creado'); qc.invalidateQueries(['gui-users']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/users/${id}`, data),
    onSuccess: () => { toast.success('Usuario actualizado'); qc.invalidateQueries(['gui-users']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/users/${id}`),
    onSuccess: () => { toast.success('Usuario eliminado'); qc.invalidateQueries(['gui-users']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios de la GUI</h1>
          <p className="text-gray-500 text-sm">{users.length} usuarios registrados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo usuario</button>
      </div>

      <Table headers={['Nombre', 'Email', 'Rol', 'Extensión', 'Estado', 'Acciones']} loading={isLoading}>
        {users.map(u => (
          <Tr key={u.id}>
            <Td><span className="font-medium">{u.name}</span></Td>
            <Td>{u.email}</Td>
            <Td><Badge variant={ROLE_COLORS[u.role]}>{u.role}</Badge></Td>
            <Td>{u.extension || <span className="text-gray-300">—</span>}</Td>
            <Td><Badge variant={u.is_active ? 'green' : 'gray'}>{u.is_active ? 'Activo' : 'Inactivo'}</Badge></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: u })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(u.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo usuario">
        <UserForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`}>
        {modal?.edit && <UserForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
