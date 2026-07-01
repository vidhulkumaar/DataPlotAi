import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import s from './AuthPages.module.css'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault()
    if (form.password !== form.confirm) { toast.error('Passwords do not match'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await register(form.email, form.password, form.full_name)
      toast.success('Account created!')
      navigate('/overview')
    } catch {
      toast.error('Registration failed — email may already be in use')
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
        <h1 className={s.title}>Create your account</h1>
        <p className={s.sub}>Start your AI analytics journey</p>

        <form onSubmit={submit} className={s.form}>
          <div className={s.field}>
            <label className={s.label}>Full name</label>
            <input
              type="text" autoFocus
              className={s.input}
              placeholder="Jane Doe"
              value={form.full_name}
              onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
            />
          </div>
          <div className={s.field}>
            <label className={s.label}>Email</label>
            <input
              type="email" required
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
              placeholder="Min. 8 characters"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            />
          </div>
          <div className={s.field}>
            <label className={s.label}>Confirm password</label>
            <input
              type="password" required
              className={s.input}
              placeholder="Repeat password"
              value={form.confirm}
              onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
            />
          </div>
          <button type="submit" className={s.btn} disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className={s.footer}>
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
