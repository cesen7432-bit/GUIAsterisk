import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Trash2, Play } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'

function fmtSize(b) {
  if (b > 1048576) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1024).toFixed(0)} KB`
}

export default function Recordings() {
  const [filter, setFilter] = useState('')
  const qc = useQueryClient()

  const { data: recordings = [], isLoading } = useQuery({
    queryKey: ['recordings', filter],
    queryFn: () => api.get(`/recordings/?src=${filter}`).then(r => r.data),
    refetchInterval: 30000,
  })

  const deleteMut = useMutation({
    mutationFn: (name) => api.delete(`/recordings/${encodeURIComponent(name)}`),
    onSuccess: () => { toast.success('Grabación eliminada'); qc.invalidateQueries(['recordings']) },
    onError: () => toast.error('Error al eliminar'),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grabaciones</h1>
          <p className="text-gray-500 text-sm">{recordings.length} archivos</p>
        </div>
        <input className="input w-56" placeholder="Filtrar por nombre..." value={filter}
          onChange={e => setFilter(e.target.value)} />
      </div>

      <Table headers={['Archivo', 'Tamaño', 'Fecha', 'Acciones']} loading={isLoading}>
        {recordings.map((r, i) => (
          <Tr key={i}>
            <Td><span className="font-mono text-xs">{r.name}</span></Td>
            <Td>{fmtSize(r.size)}</Td>
            <Td>
              <span className="text-xs">
                {format(new Date(r.created * 1000), 'dd/MM/yyyy HH:mm')}
              </span>
            </Td>
            <Td>
              <div className="flex gap-2">
                <a href={`/api/recordings/${encodeURIComponent(r.name)}/download`}
                  className="p-1.5 rounded hover:bg-blue-50 text-blue-600" title="Descargar">
                  <Download size={14} />
                </a>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(r.name) }}
                  className="p-1.5 rounded hover:bg-red-50 text-red-500" title="Eliminar">
                  <Trash2 size={14} />
                </button>
              </div>
            </Td>
          </Tr>
        ))}
      </Table>
    </div>
  )
}
