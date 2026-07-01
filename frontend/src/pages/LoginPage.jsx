import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import s from './AuthPages.module.css'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(form.email, form.password)
      navigate('/overview')
    } catch {
      toast.error('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={s.page}>
      <div className={s.card}>
        <div className={s.brand}>
          <div className={s.brandIcon}><Zap size={20} color="#7EB8F7" /></div>
          <span className={s.brandName}>DataPilot AI</span>
        </div>
        <h1 className={s.title}>Sign in to your account</h1>
        <p className={s.sub}>Welcome back — your data is waiting</p>

        <form onSubmit={submit} className={s.form}>
          <div className={s.field}>
            <label className={s.label}>Email</label>
            <input
              type="email" required autoFocus
              className={s.input}
              placeholder="you@company.com"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div className={s.field}>
            <label className={s.label}>Password</label>
            <input
              type="password" required
              className={s.input}
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            />
          </div>
          <button type="submit" className={s.btn} disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className={s.footer}>
          Don't have an account?{' '}
          <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  )
}
