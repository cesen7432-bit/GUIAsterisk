import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Download, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'

function fmtSize(b) {
  if (!b) return '—'
  if (b > 1048576) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1024).toFixed(0)} KB`
}

export default function Sounds() {
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)
  const qc = useQueryClient()

  const { data: sounds = [], isLoading } = useQuery({
    queryKey: ['sounds'],
    queryFn: () => api.get('/sounds/').then(r => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/sounds/${id}`),
    onSuccess: () => { toast.success('Audio eliminado'); qc.invalidateQueries(['sounds']) },
  })

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/sounds/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success(`Audio "${file.name}" subido y convertido`)
      qc.invalidateQueries(['sounds'])
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al subir')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audios / Sonidos</h1>
          <p className="text-gray-500 text-sm">{sounds.length} archivos de audio</p>
        </div>
        <div>
          <input type="file" ref={fileRef} className="hidden" accept=".wav,.mp3,.gsm" onChange={handleUpload} />
          <button
            className="btn-primary"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} />
            {uploading ? 'Subiendo...' : 'Subir audio'}
          </button>
        </div>
      </div>

      <div className="card bg-blue-50 border-blue-200 text-sm text-blue-800">
        Los archivos se convierten automáticamente a formato Asterisk (8kHz, mono, ulaw) usando SoX.
      </div>

      <Table headers={['Nombre', 'Archivo', 'Tamaño', 'Fecha', 'Acciones']} loading={isLoading}>
        {sounds.map(s => (
          <Tr key={s.id}>
            <Td><span className="font-medium">{s.name}</span></Td>
            <Td><span className="font-mono text-xs text-gray-500">{s.filename}</span></Td>
            <Td>{fmtSize(s.size)}</Td>
            <Td>
              <span className="text-xs">
                {s.created_at ? format(new Date(s.created_at), 'dd/MM/yyyy') : '—'}
              </span>
            </Td>
            <Td>
              <div className="flex gap-2">
                <a href={`/api/sounds/${s.id}/download`} className="p-1.5 rounded hover:bg-blue-50 text-blue-600" title="Descargar">
                  <Download size={14} />
                </a>
                <button onClick={() => { if (confirm('¿Eliminar?')) deleteMut.mutate(s.id) }} className="p-1.5 rounded hover:bg-red-50 text-red-500">
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
