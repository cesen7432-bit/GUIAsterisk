import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, Eye, Volume2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'
import { Modal } from '../components/UI/Modal'
import { FormField, Input, Select, Checkbox } from '../components/UI/FormField'

const STATUS_COLORS = { registered: 'green', unregistered: 'gray', unavailable: 'red', busy: 'yellow' }

function ExtensionForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, formState: { errors } } = useForm({ defaultValues: initial || {
    type: 'sip', context: 'from-internal', codecs: 'ulaw,alaw',
    recording: 'never', language: 'es',
    voicemail_enabled: false, followme_enabled: false, blacklist_enabled: false,
  }})

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Número" required error={errors.number?.message}>
          <input className="input" {...register('number', { required: 'Requerido' })} placeholder="100" />
        </FormField>
        <FormField label="Nombre" required>
          <input className="input" {...register('name', { required: true })} placeholder="Juan Pérez" />
        </FormField>
        <FormField label="Contraseña" required={!initial}>
          <input className="input" type="password" {...register('password', { required: !initial })} />
        </FormField>
        <FormField label="CallerID">
          <input className="input" {...register('callerid')} placeholder="Juan Pérez" />
        </FormField>
        <FormField label="Tipo">
          <select className="input" {...register('type')}>
            <option value="sip">SIP</option>
            <option value="webrtc">WebRTC</option>
          </select>
        </FormField>
        <FormField label="Idioma">
          <select className="input" {...register('language')}>
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
        </FormField>
        <FormField label="Codecs">
          <input className="input" {...register('codecs')} placeholder="ulaw,alaw,g722" />
        </FormField>
        <FormField label="Grabación">
          <select className="input" {...register('recording')}>
            <option value="never">Nunca</option>
            <option value="always">Siempre</option>
            <option value="ondemand">Bajo demanda</option>
          </select>
        </FormField>
      </div>
      <div className="flex gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('voicemail_enabled')} className="rounded" />
          Buzón de voz
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('followme_enabled')} className="rounded" />
          Sígueme
        </label>
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input type="checkbox" {...register('blacklist_enabled')} className="rounded" />
          Lista negra personal
        </label>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </form>
  )
}

export default function Extensions() {
  const [modal, setModal] = useState(null) // null | 'create' | {edit: ext}
  const qc = useQueryClient()

  const { data: extensions = [], isLoading } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => api.get('/extensions/').then(r => r.data),
    refetchInterval: 10000,
  })

  const createMut = useMutation({
    mutationFn: (data) => api.post('/extensions/', data),
    onSuccess: () => { toast.success('Extensión creada'); qc.invalidateQueries(['extensions']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/extensions/${id}`, data),
    onSuccess: () => { toast.success('Extensión actualizada'); qc.invalidateQueries(['extensions']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/extensions/${id}`),
    onSuccess: () => { toast.success('Extensión eliminada'); qc.invalidateQueries(['extensions']) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Extensiones</h1>
          <p className="text-gray-500 text-sm">{extensions.length} extensiones configuradas</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}>
          <Plus size={16} /> Nueva extensión
        </button>
      </div>

      <Table headers={['Número', 'Nombre', 'Tipo', 'Codecs', 'Grabación', 'Opciones', 'Acciones']} loading={isLoading}>
        {extensions.map(ext => (
          <Tr key={ext.id}>
            <Td><span className="font-mono font-bold text-blue-700">{ext.number}</span></Td>
            <Td>{ext.name}</Td>
            <Td><Badge variant={ext.type === 'webrtc' ? 'purple' : 'blue'}>{ext.type.toUpperCase()}</Badge></Td>
            <Td><span className="text-xs text-gray-500">{ext.codecs}</span></Td>
            <Td><Badge variant={ext.recording === 'always' ? 'red' : ext.recording === 'ondemand' ? 'yellow' : 'gray'}>{ext.recording}</Badge></Td>
            <Td>
              <div className="flex gap-1">
                {ext.voicemail_enabled && <Badge variant="blue" dot>VM</Badge>}
                {ext.followme_enabled && <Badge variant="purple" dot>FM</Badge>}
              </div>
            </Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => setModal({ edit: ext })} className="p-1.5 rounded hover:bg-blue-50 text-blue-600">
                  <Edit2 size={14} />
                </button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(ext.id) }}
                  className="p-1.5 rounded hover:bg-red-50 text-red-500">
                  <Trash2 size={14} />
                </button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nueva extensión">
        <ExtensionForm
          onSubmit={(data) => createMut.mutate(data)}
          loading={createMut.isPending}
        />
      </Modal>

      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar extensión ${modal?.edit?.number}`}>
        {modal?.edit && (
          <ExtensionForm
            initial={modal.edit}
            onSubmit={(data) => updateMut.mutate({ id: modal.edit.id, data })}
            loading={updateMut.isPending}
          />
        )}
      </Modal>
    </div>
  )
}
