import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, RefreshCw } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

function TrunkForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit } = useForm({
    defaultValues: initial || {
      port: 5060, codecs: 'ulaw,alaw', context_in: 'from-trunk',
      registration: 'send', qualify_frequency: 60,
    }
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} placeholder="proveedor_sip" />
        </FormField>
        <FormField label="Host / IP">
          <input className="input" {...register('host', { required: true })} placeholder="sip.proveedor.com" />
        </FormField>
        <FormField label="Usuario SIP">
          <input className="input" {...register('username')} />
        </FormField>
        <FormField label="Contraseña SIP">
          <input className="input" type="password" {...register('password')} />
        </FormField>
        <FormField label="Puerto">
          <input className="input" type="number" {...register('port')} />
        </FormField>
        <FormField label="Qualify Freq (s)">
          <input className="input" type="number" {...register('qualify_frequency')} />
        </FormField>
        <FormField label="Codecs">
          <input className="input" {...register('codecs')} placeholder="ulaw,alaw,g722" />
        </FormField>
        <FormField label="Contexto entrante">
          <input className="input" {...register('context_in')} />
        </FormField>
        <FormField label="Registro">
          <select className="input" {...register('registration')}>
            <option value="send">Send (enviar)</option>
            <option value="receive">Receive (recibir)</option>
            <option value="none">None</option>
          </select>
        </FormField>
      </div>
      <div className="flex gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('match_ip')} className="rounded" />
          Identificar por IP
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('direct_media')} className="rounded" />
          Direct Media
        </label>
      </div>
      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </form>
  )
}

export default function Trunks() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: trunks = [], isLoading } = useQuery({
    queryKey: ['trunks'],
    queryFn: () => api.get('/trunks/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (data) => api.post('/trunks/', data),
    onSuccess: () => { toast.success('Trunk creado'); qc.invalidateQueries(['trunks']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/trunks/${id}`, data),
    onSuccess: () => { toast.success('Trunk actualizado'); qc.invalidateQueries(['trunks']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/trunks/${id}`),
    onSuccess: () => { toast.success('Trunk eliminado'); qc.invalidateQueries(['trunks']) },
  })

  const registerMut = useMutation({
    mutationFn: (id) => api.post(`/trunks/${id}/register`),
    onSuccess: () => toast.success('Registro forzado enviado'),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Troncales (Trunks)</h1>
          <p className="text-gray-500 text-sm">{trunks.length} troncales configurados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}>
          <Plus size={16} /> Nuevo trunk
        </button>
      </div>

      <Table headers={['Nombre', 'Host', 'Puerto', 'Codecs', 'Registro', 'Qualify', 'Acciones']} loading={isLoading}>
        {trunks.map(t => (
          <Tr key={t.id}>
            <Td><span className="font-medium text-gray-900">{t.name}</span></Td>
            <Td><span className="font-mono text-sm">{t.host}</span></Td>
            <Td>{t.port}</Td>
            <Td><span className="text-xs text-gray-500">{t.codecs}</span></Td>
            <Td><Badge variant={t.registration === 'send' ? 'blue' : t.registration === 'receive' ? 'green' : 'gray'}>{t.registration}</Badge></Td>
            <Td>{t.qualify_frequency}s</Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => registerMut.mutate(t.id)} className="p-1.5 rounded hover:bg-green-50 text-green-600" title="Forzar registro">
                  <RefreshCw size={14} />
                </button>
                <button onClick={() => setModal({ edit: t })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600">
                  <Edit2 size={14} />
                </button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(t.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500">
                  <Trash2 size={14} />
                </button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo trunk" size="lg">
        <TrunkForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && <TrunkForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
