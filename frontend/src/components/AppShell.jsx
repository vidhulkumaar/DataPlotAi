import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard, Upload, Database, Cpu, BarChart3,
  MessageSquare, LogOut, ChevronRight, Zap
} from 'lucide-react'
import styles from './AppShell.module.css'

const nav = [
  { to: '/overview',     label: 'Overview',    icon: LayoutDashboard },
  { to: '/data-source',  label: 'Data Source',  icon: Upload },
  { to: '/pipeline',     label: 'AI Pipeline',  icon: Cpu },
  { to: '/dashboard',    label: 'Dashboards',   icon: BarChart3 },
  { to: '/chat',         label: 'AI Chatbot',   icon: MessageSquare },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => { logout(); navigate('/login') }

  const pageTitle = nav.find(n => location.pathname.startsWith(n.to))?.label || 'DataPilot AI'

  return (
    <div className={styles.shell}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <Zap size={16} color="#7EB8F7" />
          </div>
          <span className={styles.logoText}>DataPilot AI</span>
        </div>

        <nav className={styles.nav}>
          <div className={styles.navSection}>
            <span className={styles.navLabel}>Workspace</span>
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `${styles.navItem} ${isActive ? styles.navItemActive : ''}`
                }
              >
                <Icon size={15} className={styles.navIcon} />
                {label}
              </NavLink>
            ))}
          </div>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userPill}>
            <div className={styles.avatar}>
              {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className={styles.userInfo}>
              <span className={styles.userName}>{user?.full_name || 'User'}</span>
              <span className={styles.userEmail}>{user?.email}</span>
            </div>
            <button className={styles.logoutBtn} onClick={handleLogout} title="Log out">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className={styles.main}>
        <header className={styles.topbar}>
          <h1 className={styles.pageTitle}>{pageTitle}</h1>
          <div className={styles.topbarRight}>
            <div className={styles.aiBadge}>
              <Zap size={10} />
              Gemini AI Active
            </div>
          </div>
        </header>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
