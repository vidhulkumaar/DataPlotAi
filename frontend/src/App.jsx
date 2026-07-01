import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import AppShell from './components/AppShell'
import OverviewPage from './pages/OverviewPage'
import DataSourcePage from './pages/DataSourcePage'
import PipelinePage from './pages/PipelinePage'
import DashboardPage from './pages/DashboardPage'
import ChatPage from './pages/ChatPage'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',color:'var(--gray-500)' }}>Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="data-source" element={<DataSourcePage />} />
          <Route path="pipeline/:datasetId" element={<PipelinePage />} />
          <Route path="dashboard/:datasetId?" element={<DashboardPage />} />
          <Route path="chat/:datasetId?" element={<ChatPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
