import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, CheckCircle, XCircle } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

function ARIUserForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({
    defaultValues: initial || { permissions: 'read_write', password_format: 'plain', cors_origins: '*', is_active: true }
  })
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Usuario" required>
          <input className="input" {...register('username', { required: !initial })} readOnly={!!initial} />
        </FormField>
        <FormField label="Contraseña" required={!initial}>
          <input className="input" type="password" {...register('password')} />
        </FormField>
        <FormField label="Formato contraseña">
          <select className="input" {...register('password_format')}>
            <option value="plain">Plain text</option>
            <option value="crypt">Crypt</option>
          </select>
        </FormField>
        <FormField label="Permisos">
          <select className="input" {...register('permissions')}>
            <option value="read_write">read_write (control total)</option>
            <option value="read_only">read_only (solo consulta)</option>
          </select>
        </FormField>
        <FormField label="Aplicaciones Stasis (vacío = todas)">
          <input className="input" {...register('stasis_apps')} placeholder="app1,app2" />
        </FormField>
        <FormField label="CORS Origins">
          <input className="input" {...register('cors_origins')} placeholder="* o https://miapp.com" />
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

export default function ARIUsers() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['ari-users'],
    queryFn: () => api.get('/ari/users').then(r => r.data),
  })

  const { data: apps = [] } = useQuery({
    queryKey: ['ari-apps'],
    queryFn: () => api.get('/ari/apps').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/ari/users', d),
    onSuccess: () => { toast.success('Usuario ARI creado'); qc.invalidateQueries(['ari-users']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ username, data }) => api.put(`/ari/users/${username}`, data),
    onSuccess: () => { toast.success('Actualizado'); qc.invalidateQueries(['ari-users']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (username) => api.delete(`/ari/users/${username}`),
    onSuccess: () => { toast.success('Eliminado'); qc.invalidateQueries(['ari-users']) },
  })

  const testMut = useMutation({
    mutationFn: () => api.post('/ari/test'),
    onSuccess: (r) => {
      const info = r.data
      if (info.ok) toast.success(`ARI OK — Asterisk ${info.info?.build?.version}`)
      else toast.error(`ARI Error: ${info.error}`)
    },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios ARI</h1>
          <p className="text-gray-500 text-sm">{users.length} usuarios configurados</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => testMut.mutate()} disabled={testMut.isPending}>
            Probar conexión ARI
          </button>
          <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo</button>
        </div>
      </div>

      {apps.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">Aplicaciones Stasis activas ({apps.length})</h3>
          <div className="flex flex-wrap gap-2">
            {apps.map(app => (
              <Badge key={app.name} variant="green" dot>{app.name}</Badge>
            ))}
          </div>
        </div>
      )}

      <Table headers={['Usuario', 'Permisos', 'Formato', 'CORS', 'Estado', 'Acciones']} loading={isLoading}>
        {users.map(u => (
          <Tr key={u.id}>
            <Td><span className="font-mono font-bold">{u.username}</span></Td>
            <Td><Badge variant={u.permissions === 'read_write' ? 'blue' : 'gray'}>{u.permissions}</Badge></Td>
            <Td>{u.password_format}</Td>
            <Td><span className="font-mono text-xs">{u.cors_origins}</span></Td>
            <Td><Badge variant={u.is_active ? 'green' : 'gray'}>{u.is_active ? 'Activo' : 'Inactivo'}</Badge></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: u })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(u.username) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo usuario ARI" size="lg">
        <ARIUserForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.username}`} size="lg">
        {modal?.edit && <ARIUserForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ username: modal.edit.username, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
