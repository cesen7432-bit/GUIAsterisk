import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { Layout } from './components/Layout/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Extensions from './pages/Extensions'
import Trunks from './pages/Trunks'
import OutboundRoutes from './pages/OutboundRoutes'
import InboundRoutes from './pages/InboundRoutes'
import IVR from './pages/IVR'
import FollowMe from './pages/FollowMe'
import Queues from './pages/Queues'
import CDR from './pages/CDR'
import Recordings from './pages/Recordings'
import Blacklist from './pages/Blacklist'
import Voicemail from './pages/Voicemail'
import Schedules from './pages/Schedules'
import Sounds from './pages/Sounds'
import SystemConfig from './pages/SystemConfig'
import GUIUsers from './pages/GUIUsers'
import Monitor from './pages/Monitor'
import ARIUsers from './pages/ARIUsers'

function RequireAuth({ children }) {
  const { token } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const { token, fetchMe } = useAuthStore()

  useEffect(() => {
    if (token) fetchMe()
  }, [token, fetchMe])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="monitor" element={<Monitor />} />
          <Route path="extensions" element={<Extensions />} />
          <Route path="trunks" element={<Trunks />} />
          <Route path="routes/outbound" element={<OutboundRoutes />} />
          <Route path="routes/inbound" element={<InboundRoutes />} />
          <Route path="ivr" element={<IVR />} />
          <Route path="followme" element={<FollowMe />} />
          <Route path="queues" element={<Queues />} />
          <Route path="cdr" element={<CDR />} />
          <Route path="recordings" element={<Recordings />} />
          <Route path="blacklist" element={<Blacklist />} />
          <Route path="voicemail" element={<Voicemail />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="sounds" element={<Sounds />} />
          <Route path="system" element={<SystemConfig />} />
          <Route path="users" element={<GUIUsers />} />
          <Route path="ari" element={<ARIUsers />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
