import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

export default function Blacklist() {
  const [modal, setModal] = useState(false)
  const qc = useQueryClient()
  const { register, handleSubmit, reset } = useForm()

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['blacklist'],
    queryFn: () => api.get('/blacklist/').then(r => r.data),
  })

  const addMut = useMutation({
    mutationFn: (data) => api.post('/blacklist/', data),
    onSuccess: () => { toast.success('Número bloqueado'); qc.invalidateQueries(['blacklist']); setModal(false); reset() },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const delMut = useMutation({
    mutationFn: (number) => api.delete(`/blacklist/${encodeURIComponent(number)}`),
    onSuccess: () => { toast.success('Número desbloqueado'); qc.invalidateQueries(['blacklist']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lista Negra</h1>
          <p className="text-gray-500 text-sm">{items.length} números bloqueados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal(true)}>
          <Plus size={16} /> Agregar número
        </button>
      </div>

      <Table headers={['Número', 'Motivo', 'Fecha', 'Acción']} loading={isLoading}>
        {items.map(b => (
          <Tr key={b.id}>
            <Td><span className="font-mono font-bold">{b.number}</span></Td>
            <Td>{b.reason || <span className="text-gray-300">—</span>}</Td>
            <Td><span className="text-xs">{b.created_at ? format(new Date(b.created_at), 'dd/MM/yyyy') : '—'}</span></Td>
            <Td>
              <button onClick={() => { if (confirm('¿Desbloquear?')) delMut.mutate(b.number) }}
                className="p-1.5 rounded hover:bg-red-50 text-red-500">
                <Trash2 size={14} />
              </button>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal} onClose={() => setModal(false)} title="Bloquear número" size="sm">
        <form onSubmit={handleSubmit(d => addMut.mutate(d))} className="space-y-4">
          <FormField label="Número" required>
            <input className="input" {...register('number', { required: true })} placeholder="+521234567890" autoFocus />
          </FormField>
          <FormField label="Motivo (opcional)">
            <input className="input" {...register('reason')} placeholder="Spam, acoso..." />
          </FormField>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setModal(false)}>Cancelar</button>
            <button type="submit" className="btn-danger" disabled={addMut.isPending}>Bloquear</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
