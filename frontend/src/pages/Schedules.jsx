import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { useForm, useFieldArray } from 'react-hook-form'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Modal } from '../components/UI/Modal'
import { FormField } from '../components/UI/FormField'

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function ScheduleForm({ initial, onSubmit, loading }) {
  const { register, handleSubmit, control } = useForm({
    defaultValues: initial || { hours: [], holidays: [] }
  })
  const hours = useFieldArray({ control, name: 'hours' })
  const holidays = useFieldArray({ control, name: 'holidays' })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <FormField label="Nombre del horario" required>
        <input className="input" {...register('name', { required: true })} />
      </FormField>

      <div className="grid grid-cols-3 gap-4">
        <FormField label="Destino en horario">
          <input className="input" {...register('dest_open_type')} placeholder="extension" />
          <input className="input mt-1" {...register('dest_open_id')} placeholder="ID (ej: 100)" />
        </FormField>
        <FormField label="Destino fuera de horario">
          <input className="input" {...register('dest_closed_type')} placeholder="voicemail" />
          <input className="input mt-1" {...register('dest_closed_id')} placeholder="ID" />
        </FormField>
        <FormField label="Destino en festivos">
          <input className="input" {...register('dest_holiday_type')} placeholder="ivr" />
          <input className="input mt-1" {...register('dest_holiday_id')} placeholder="ID" />
        </FormField>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Días y horarios de atención</label>
          <button type="button" className="btn-secondary text-xs py-1" onClick={() => hours.append({ day_of_week: 0, start_time: '09:00', end_time: '18:00' })}>
            <Plus size={12} /> Agregar día
          </button>
        </div>
        <div className="space-y-2">
          {hours.fields.map((f, i) => (
            <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
              <select className="input col-span-4" {...register(`hours.${i}.day_of_week`, { valueAsNumber: true })}>
                {DAYS.map((d, j) => <option key={j} value={j}>{d}</option>)}
              </select>
              <input className="input col-span-3" type="time" {...register(`hours.${i}.start_time`)} />
              <span className="col-span-1 text-center text-gray-400 text-sm">—</span>
              <input className="input col-span-3" type="time" {...register(`hours.${i}.end_time`)} />
              <button type="button" onClick={() => hours.remove(i)} className="col-span-1 p-1.5 text-red-500 hover:bg-red-50 rounded"><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Días festivos</label>
          <button type="button" className="btn-secondary text-xs py-1" onClick={() => holidays.append({ date: '', description: '' })}>
            <Plus size={12} /> Agregar festivo
          </button>
        </div>
        <div className="space-y-2">
          {holidays.fields.map((f, i) => (
            <div key={f.id} className="grid grid-cols-12 gap-2 items-center">
              <input className="input col-span-4" type="date" {...register(`holidays.${i}.date`)} />
              <input className="input col-span-7" {...register(`holidays.${i}.description`)} placeholder="Descripción (ej: Año Nuevo)" />
              <button type="button" onClick={() => holidays.remove(i)} className="col-span-1 p-1.5 text-red-500 hover:bg-red-50 rounded"><Trash2 size={14} /></button>
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

export default function Schedules() {
  const [modal, setModal] = useState(null)
  const qc = useQueryClient()

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => api.get('/schedules/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/schedules/', d),
    onSuccess: () => { toast.success('Horario creado'); qc.invalidateQueries(['schedules']); setModal(null) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Error'),
  })

  const loadSchedule = async (s) => {
    const { data } = await api.get(`/schedules/${s.id}`)
    setModal({ edit: data })
  }

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => api.put(`/schedules/${id}`, data),
    onSuccess: () => { toast.success('Horario actualizado'); qc.invalidateQueries(['schedules']); setModal(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/schedules/${id}`),
    onSuccess: () => { toast.success('Horario eliminado'); qc.invalidateQueries(['schedules']) },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Horarios y Calendarios</h1>
          <p className="text-gray-500 text-sm">{schedules.length} horarios configurados</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}><Plus size={16} /> Nuevo horario</button>
      </div>

      <Table headers={['Nombre', 'Acciones']} loading={isLoading}>
        {schedules.map(s => (
          <Tr key={s.id}>
            <Td><span className="font-medium">{s.name}</span></Td>
            <Td>
              <div className="flex gap-2">
                <button onClick={() => loadSchedule(s)} className="p-1.5 rounded hover:bg-blue-50 text-blue-600"><Edit2 size={14} /></button>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(s.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 size={14} /></button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Nuevo horario" size="lg">
        <ScheduleForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Modal>
      <Modal open={!!modal?.edit} onClose={() => setModal(null)} title={`Editar: ${modal?.edit?.name}`} size="lg">
        {modal?.edit && <ScheduleForm initial={modal.edit} onSubmit={(d) => updateMut.mutate({ id: modal.edit.id, data: d })} loading={updateMut.isPending} />}
      </Modal>
    </div>
  )
}
