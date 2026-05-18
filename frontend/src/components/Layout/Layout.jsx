import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useWebSocket } from '../../hooks/useWebSocket'
import api from '../../api/client'

export function Layout() {
  const [amiConnected, setAmiConnected] = useState(false)

  useEffect(() => {
    const check = () =>
      api.get('/health')
        .then(r => setAmiConnected(r.data.ami === true))
        .catch(() => setAmiConnected(false))
    check()
    const interval = setInterval(check, 10000)
    return () => clearInterval(interval)
  }, [])

  useWebSocket((msg) => {
    if (msg.source === 'ami') setAmiConnected(true)
    if (msg.source === 'ami_disconnected') setAmiConnected(false)
  })

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header amiConnected={amiConnected} />
        <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
