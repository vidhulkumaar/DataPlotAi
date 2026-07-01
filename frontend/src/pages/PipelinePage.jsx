import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle, XCircle, Clock, Loader, ChevronRight, BarChart3 } from 'lucide-react'
import api from '../services/api'
import s from './PipelinePage.module.css'

const STEP_META = {
  ingest:             { label: 'Data ingestion',             desc: 'Parsing file and loading into data warehouse' },
  schema_extract:     { label: 'Schema extraction',          desc: 'Mapping tables, columns, and data types' },
  ai_schema_analysis: { label: 'Gemini AI schema analysis',  desc: 'Identifying metrics, dimensions, and analytics fields' },
  ai_data_selection:  { label: 'AI data selection',          desc: 'Selecting most meaningful rows and columns' },
  superset_push:      { label: 'Superset chart generation',  desc: 'Creating charts exclusively from AI-selected fields' },
  rag_embed:          { label: 'RAG embedding',              desc: 'Building vector index for chatbot retrieval' },
}

export default function PipelinePage() {
  const { datasetId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!datasetId) return
    let alive = true

    const poll = async () => {
      try {
        const { data } = await api.get(`/pipeline/${datasetId}`)
        if (!alive) return
        setStatus(data)

        // Stop polling when terminal state reached
        if (!['superset_ready', 'error'].includes(data.status)) {
          setTimeout(poll, 2500)
        }
      } catch (e) {
        if (alive) setError('Could not fetch pipeline status')
      }
    }

    poll()
    return () => { alive = false }
  }, [datasetId])

  if (error) return <div className={s.errBox}><XCircle size={16}/> {error}</div>
  if (!status) return <div className={s.loading}><Loader size={20} className="spin" /> Loading pipeline…</div>

  const allDone = status.status === 'superset_ready'
  const hasFailed = status.status === 'error'
  const progress = (() => {
    const steps = status.steps || []
    const done = steps.filter(s => s.status === 'done').length
    return Math.round((done / steps.length) * 100)
  })()

  return (
    <div className="fade-in">
      <div className={s.header}>
        <div>
          <h2 className={s.title}>AI Pipeline</h2>
          <p className={s.sub}>Processing your data through the mandatory AI pipeline</p>
        </div>
        {allDone && (
          <button className={s.viewBtn} onClick={() => navigate(`/dashboard/${datasetId}`)}>
            View dashboard <ChevronRight size={14} />
          </button>
        )}
      </div>

      {/* Overall progress */}
      <div className={s.progressCard}>
        <div className={s.progressHeader}>
          <div className={s.progressLabel}>
            {allDone ? 'Pipeline complete' : hasFailed ? 'Pipeline failed' : 'Processing…'}
          </div>
          <span className={`${s.statusBadge} ${allDone ? s.badgeGreen : hasFailed ? s.badgeRed : s.badgeBlue}`}>
            {allDone ? 'Ready' : hasFailed ? 'Error' : `${progress}%`}
          </span>
        </div>
        <div className={s.progressBar}>
          <div
            className={`${s.progressFill} ${hasFailed ? s.progressFillRed : ''}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className={s.progressSub}>
          {allDone
            ? 'Dashboard generated — charts created from AI-selected fields only'
            : hasFailed
            ? 'An error occurred during processing'
            : 'Gemini AI is analyzing your data — this may take 30–60 seconds'}
        </div>
      </div>

      <div className={s.grid}>
        {/* Steps */}
        <div className={s.stepsCard}>
          <h3 className={s.cardTitle}>Pipeline steps</h3>
          {(status.steps || []).map((step, i) => {
            const meta = STEP_META[step.step] || { label: step.step, desc: '' }
            return (
              <div key={step.step} className={s.step}>
                <div className={s.stepIcon}>
                  {step.status === 'done'    && <CheckCircle size={16} className={s.iconDone} />}
                  {step.status === 'running' && <Loader size={16} className={`${s.iconRunning} spin`} />}
                  {step.status === 'error'   && <XCircle size={16} className={s.iconError} />}
                  {step.status === 'pending' && <Clock size={16} className={s.iconPending} />}
                </div>
                <div className={s.stepBody}>
                  <div className={`${s.stepLabel} ${step.status === 'running' ? s.stepLabelActive : ''}`}>
                    {meta.label}
                  </div>
                  <div className={s.stepDesc}>
                    {step.detail || meta.desc}
                  </div>
                  {step.status === 'running' && (
                    <div className={s.miniProgress}>
                      <div className={s.miniProgressFill} style={{ animation: 'indeterminate 1.5s ease infinite' }} />
                    </div>
                  )}
                </div>
                <span className={`${s.stepBadge} ${s[`badge_${step.status}`]}`}>
                  {step.status}
                </span>
              </div>
            )
          })}
        </div>

        {/* AI schema preview */}
        <div>
          {status.ai_schema && (
            <div className={s.schemaCard}>
              <h3 className={s.cardTitle}>AI schema analysis</h3>
              {status.ai_schema.data_summary && (
                <div className={s.aiSummary}>
                  <div className={s.aiSummaryLabel}>Gemini says:</div>
                  "{status.ai_schema.data_summary}"
                </div>
              )}

              {status.ai_schema.selected_columns?.length > 0 && (
                <>
                  <div className={s.schemaHeader}>
                    <span>Column</span><span>Type</span><span>Role</span>
                  </div>
                  {status.ai_schema.selected_columns.slice(0, 10).map(col => (
                    <div key={col.name} className={s.schemaRow}>
                      <span className={s.colName}>{col.name}</span>
                      <span className={s.colType}>{col.sql_type}</span>
                      <RoleBadge role={col.role} />
                    </div>
                  ))}
                  {status.ai_schema.selected_columns.length > 10 && (
                    <div className={s.moreRows}>+{status.ai_schema.selected_columns.length - 10} more columns</div>
                  )}
                </>
              )}

              {status.ai_schema.suggested_charts?.length > 0 && (
                <>
                  <div className={s.chartsTitle}>
                    <BarChart3 size={13} /> Suggested charts ({status.ai_schema.suggested_charts.length})
                  </div>
                  {status.ai_schema.suggested_charts.map((ch, i) => (
                    <div key={i} className={s.chartRow}>
                      <div className={s.chartIcon}>{chartEmoji(ch.chart_type)}</div>
                      <div>
                        <div className={s.chartTitle}>{ch.title}</div>
                        <div className={s.chartReason}>{ch.reasoning}</div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}

          {allDone && (
            <div className={s.readyCard}>
              <CheckCircle size={20} className={s.readyIcon} />
              <div className={s.readyTitle}>Dashboard ready</div>
              <div className={s.readySub}>All charts generated from AI-selected fields</div>
              <button className={s.viewBtn} onClick={() => navigate(`/dashboard/${datasetId}`)}>
                Open dashboard <ChevronRight size={14} />
              </button>
              <button className={s.chatBtn} onClick={() => navigate(`/chat/${datasetId}`)}>
                Chat with your data →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function RoleBadge({ role }) {
  const map = {
    metric:    [s.roleMetric, 'Metric'],
    dimension: [s.roleDim, 'Dimension'],
    skip:      [s.roleSkip, 'Skipped'],
  }
  const [cls, label] = map[role] || [s.roleSkip, role]
  return <span className={`${s.roleBadge} ${cls}`}>{label}</span>
}

function chartEmoji(type) {
  return { bar:'📊', line:'📈', pie:'🥧', area:'📉', scatter:'🔵', table:'📋', big_number:'🔢' }[type] || '📊'
}
