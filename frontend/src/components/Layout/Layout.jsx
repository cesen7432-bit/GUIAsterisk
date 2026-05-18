import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useWebSocket } from '../../hooks/useWebSocket'

export function Layout() {
  const [amiConnected, setAmiConnected] = useState(false)

  useWebSocket((msg) => {
    if (msg.source === 'ami' && msg.event?.Event === 'FullyBooted') {
      setAmiConnected(true)
    }
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
