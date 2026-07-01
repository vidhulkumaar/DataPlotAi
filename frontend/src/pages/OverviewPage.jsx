import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Database, MessageSquare, Zap, ArrowRight, Plus } from 'lucide-react'
import api from '../services/api'
import s from './OverviewPage.module.css'

export default function OverviewPage() {
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/ingest/datasets')
      .then(r => setDatasets(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const ready = datasets.filter(d => d.status === 'superset_ready')
  const processing = datasets.filter(d => ['pending','ingested','ai_analyzing','ai_done'].includes(d.status))
  const totalCharts = ready.reduce((acc, d) => acc + (d.ai_schema?.suggested_charts?.length || 0), 0)

  return (
    <div className="fade-in">
      <div className={s.header}>
        <div>
          <h2 className={s.title}>Welcome back</h2>
          <p className={s.sub}>Your AI-powered analytics platform</p>
        </div>
        <button className={s.newBtn} onClick={() => navigate('/data-source')}>
          <Plus size={14} /> New dataset
        </button>
      </div>

      {/* Stats */}
      <div className={s.stats}>
        <StatCard icon={<Database size={18} />} label="Active datasets" value={ready.length} color="navy" />
        <StatCard icon={<BarChart3 size={18} />} label="AI charts generated" value={totalCharts} color="green" />
        <StatCard icon={<MessageSquare size={18} />} label="Mode" value="RAG Chatbot" color="purple" sub="Always on" />
        <StatCard icon={<Zap size={18} />} label="AI engine" value="Gemini" color="amber" sub="1.5 Pro" />
      </div>

      <div className={s.grid}>
        {/* Datasets */}
        <div className={s.card}>
          <div className={s.cardHeader}>
            <span className={s.cardTitle}>Datasets</span>
            <button className={s.linkBtn} onClick={() => navigate('/data-source')}>
              Add <ArrowRight size={12} />
            </button>
          </div>

          {loading && <p className={s.muted}>Loading…</p>}
          {!loading && datasets.length === 0 && (
            <div className={s.empty}>
              <Database size={32} className={s.emptyIcon} />
              <p>No datasets yet</p>
              <button className={s.emptyBtn} onClick={() => navigate('/data-source')}>Upload or connect →</button>
            </div>
          )}

          <div className={s.datasetList}>
            {datasets.map(d => (
              <div
                key={d.id}
                className={s.datasetRow}
                onClick={() => d.status === 'superset_ready'
                  ? navigate(`/dashboard/${d.id}`)
                  : navigate(`/pipeline/${d.id}`)
                }
              >
                <div className={s.datasetIcon}>
                  {['csv','excel','sql_dump'].includes(d.source_type) ? '📄' : '🗄️'}
                </div>
                <div className={s.datasetInfo}>
                  <span className={s.datasetName}>{d.name}</span>
                  <span className={s.datasetMeta}>
                    {d.row_count?.toLocaleString()} rows · {d.source_type}
                  </span>
                </div>
                <StatusBadge status={d.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Processing */}
        <div className={s.card}>
          <div className={s.cardHeader}>
            <span className={s.cardTitle}>AI pipeline activity</span>
          </div>
          {processing.length === 0 ? (
            <div className={s.empty}>
              <Zap size={28} className={s.emptyIcon} />
              <p>No active pipelines</p>
            </div>
          ) : (
            processing.map(d => (
              <div key={d.id} className={s.pipelineRow}
                onClick={() => navigate(`/pipeline/${d.id}`)}>
                <div>
                  <div className={s.datasetName}>{d.name}</div>
                  <div className={s.datasetMeta}>{statusLabel(d.status)}</div>
                </div>
                <div className={s.spinner} />
              </div>
            ))
          )}

          <div className={s.cardHeader} style={{ marginTop: 20 }}>
            <span className={s.cardTitle}>How it works</span>
          </div>
          {['Upload or connect data', 'Gemini AI analyzes schema', 'AI selects key columns & rows',
            'Superset generates charts', 'Chat with your data via RAG'].map((step, i) => (
            <div key={i} className={s.howStep}>
              <div className={s.stepNum}>{i + 1}</div>
              <span className={s.stepText}>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color, sub }) {
  return (
    <div className={`${s.statCard} ${s[`stat_${color}`]}`}>
      <div className={s.statIcon}>{icon}</div>
      <div>
        <div className={s.statValue}>{value}</div>
        <div className={s.statLabel}>{label}</div>
        {sub && <div className={s.statSub}>{sub}</div>}
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    superset_ready: ['Ready', s.badgeGreen],
    ai_analyzing:   ['Analyzing', s.badgeBlue],
    ai_done:        ['AI done', s.badgeBlue],
    ingested:       ['Ingested', s.badgeGray],
    pending:        ['Pending', s.badgeGray],
    error:          ['Error', s.badgeRed],
  }
  const [label, cls] = map[status] || ['Unknown', s.badgeGray]
  return <span className={`${s.badge} ${cls}`}>{label}</span>
}

function statusLabel(s) {
  const m = { pending:'Queued', ingested:'Data loaded', ai_analyzing:'Gemini analyzing…',
    ai_done:'AI complete', superset_ready:'Dashboard ready', error:'Failed' }
  return m[s] || s
}
