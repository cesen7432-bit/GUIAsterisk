import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Filter } from 'lucide-react'
import { format } from 'date-fns'
import api from '../api/client'
import { Table, Td, Tr } from '../components/UI/Table'
import { Badge } from '../components/UI/Badge'

const DISP_COLORS = { ANSWERED: 'green', 'NO ANSWER': 'yellow', BUSY: 'red', FAILED: 'gray' }

export default function CDR() {
  const [filters, setFilters] = useState({ src: '', dst: '', disposition: '', date_from: '', date_to: '' })
  const [applied, setApplied] = useState({})

  const { data: records = [], isLoading } = useQuery({
    queryKey: ['cdr', applied],
    queryFn: () => {
      const params = new URLSearchParams()
      Object.entries(applied).forEach(([k, v]) => { if (v) params.append(k, v) })
      params.append('limit', '200')
      return api.get(`/cdr/?${params}`).then(r => r.data)
    },
  })

  const { data: stats } = useQuery({
    queryKey: ['cdr-stats-filtered', applied],
    queryFn: () => {
      const params = new URLSearchParams()
      if (applied.date_from) params.append('date_from', applied.date_from)
      if (applied.date_to) params.append('date_to', applied.date_to)
      return api.get(`/cdr/stats?${params}`).then(r => r.data)
    },
  })

  const handleExport = (fmt) => {
    const params = new URLSearchParams({ ...applied, fmt })
    window.open(`/api/cdr/export?${params}`)
  }

  const fmtDate = (d) => {
    try { return format(new Date(d), 'dd/MM/yyyy HH:mm:ss') } catch { return d }
  }

  const fmtDur = (s) => {
    const m = Math.floor(s / 60), sec = s % 60
    return `${m}:${String(sec).padStart(2, '0')}`
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Registros de llamadas (CDR)</h1>
          <p className="text-gray-500 text-sm">{records.length} registros</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => handleExport('csv')} className="btn-secondary">
            <Download size={14} /> CSV
          </button>
          <button onClick={() => handleExport('pdf')} className="btn-secondary">
            <Download size={14} /> PDF
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-sm text-gray-500">Total llamadas</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{stats.answered}</p>
            <p className="text-sm text-gray-500">Contestadas</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-red-600">{stats.no_answer}</p>
            <p className="text-sm text-gray-500">No contestadas</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="label">Origen</label>
            <input className="input" value={filters.src} onChange={e => setFilters(p => ({...p, src: e.target.value}))} placeholder="Extensión" />
          </div>
          <div>
            <label className="label">Destino</label>
            <input className="input" value={filters.dst} onChange={e => setFilters(p => ({...p, dst: e.target.value}))} placeholder="Número" />
          </div>
          <div>
            <label className="label">Estado</label>
            <select className="input" value={filters.disposition} onChange={e => setFilters(p => ({...p, disposition: e.target.value}))}>
              <option value="">Todos</option>
              <option value="ANSWERED">ANSWERED</option>
              <option value="NO ANSWER">NO ANSWER</option>
              <option value="BUSY">BUSY</option>
              <option value="FAILED">FAILED</option>
            </select>
          </div>
          <div>
            <label className="label">Desde</label>
            <input className="input" type="date" value={filters.date_from} onChange={e => setFilters(p => ({...p, date_from: e.target.value}))} />
          </div>
          <div>
            <label className="label">Hasta</label>
            <input className="input" type="date" value={filters.date_to} onChange={e => setFilters(p => ({...p, date_to: e.target.value}))} />
          </div>
        </div>
        <div className="flex justify-end mt-3">
          <button className="btn-primary" onClick={() => setApplied({...filters})}>
            <Filter size={14} /> Filtrar
          </button>
        </div>
      </div>

      <Table headers={['Fecha', 'Origen', 'Destino', 'Duración', 'Facturado', 'Estado', 'Grabación']} loading={isLoading}>
        {records.map((r, i) => (
          <Tr key={i}>
            <Td><span className="text-xs font-mono">{fmtDate(r.calldate)}</span></Td>
            <Td>{r.src}</Td>
            <Td>{r.dst}</Td>
            <Td>{fmtDur(r.duration || 0)}</Td>
            <Td>{fmtDur(r.billsec || 0)}</Td>
            <Td><Badge variant={DISP_COLORS[r.disposition] || 'gray'}>{r.disposition}</Badge></Td>
            <Td>
              {r.recordingfile ? (
                <a href={`/api/recordings/${encodeURIComponent(r.recordingfile)}/download`}
                  className="text-xs text-blue-600 underline">Ver</a>
              ) : <span className="text-gray-300">—</span>}
            </Td>
          </Tr>
        ))}
      </Table>
    </div>
  )
}
