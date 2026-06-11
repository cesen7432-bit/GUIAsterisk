import { useWatch } from 'react-hook-form'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'

export function DestinationIdSelect({ register, control, typeName, idName, className = '' }) {
  const destType = useWatch({ control, name: typeName })
  const cls = `input ${className}`

  const { data: extensions = [] } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => api.get('/extensions/').then(r => r.data),
    staleTime: 60000,
  })
  const { data: queues = [] } = useQuery({
    queryKey: ['queues'],
    queryFn: () => api.get('/queues/').then(r => r.data),
    staleTime: 60000,
  })
  const { data: ivrs = [] } = useQuery({
    queryKey: ['ivr'],
    queryFn: () => api.get('/ivr/').then(r => r.data),
    staleTime: 60000,
  })

  if (destType === 'hangup') {
    return <input className={cls} disabled placeholder="—" {...register(idName)} />
  }
  if (destType === 'extension' || destType === 'voicemail') {
    return (
      <select className={cls} {...register(idName)}>
        <option value="">— extensión —</option>
        {extensions.map(e => (
          <option key={e.number} value={e.number}>{e.number} – {e.name}</option>
        ))}
      </select>
    )
  }
  if (destType === 'queue') {
    return (
      <select className={cls} {...register(idName)}>
        <option value="">— cola —</option>
        {queues.map(q => (
          <option key={q.name} value={q.name}>{q.name}</option>
        ))}
      </select>
    )
  }
  if (destType === 'ivr') {
    return (
      <select className={cls} {...register(idName)}>
        <option value="">— IVR —</option>
        {ivrs.map(i => (
          <option key={i.id} value={String(i.id)}>{i.name}</option>
        ))}
      </select>
    )
  }
  return <input className={cls} {...register(idName)} placeholder="ID destino" />
}

export function SoundSelect({ register, name }) {
  const { data: sounds = [] } = useQuery({
    queryKey: ['sounds'],
    queryFn: () => api.get('/sounds/').then(r => r.data),
    staleTime: 60000,
  })
  return (
    <select className="input" {...register(name)}>
      <option value="">— sin audio —</option>
      {sounds.map(s => (
        <option key={s.id} value={s.name}>{s.name}</option>
      ))}
    </select>
  )
}

export function ExtensionSelect({ register, name, placeholder = '— extensión —', className = '' }) {
  const { data: extensions = [] } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => api.get('/extensions/').then(r => r.data),
    staleTime: 60000,
  })
  return (
    <select className={`input ${className}`} {...register(name)}>
      <option value="">{placeholder}</option>
      {extensions.map(e => (
        <option key={e.number} value={e.number}>{e.number} – {e.name}</option>
      ))}
    </select>
  )
}
