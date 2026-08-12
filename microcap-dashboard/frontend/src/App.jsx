import React, { useState, useEffect } from 'react'
import './mobile.css'

const API = '/api'

const VERDICT_COLORS = {
  shortlisted: { bg: '#052e16', border: '#166534', text: '#4ade80', badge: '#14532d' },
  borderline:  { bg: '#1c1a07', border: '#713f12', text: '#fbbf24', badge: '#451a03' },
  rejected:    { bg: '#1f0a0a', border: '#7f1d1d', text: '#f87171', badge: '#450a0a' },
  unknown:     { bg: '#1a1d27', border: '#2d3148', text: '#94a3b8', badge: '#1e293b' },
}

const AGENT_STATUS_COLORS = {
  active: { bg: '#052e16', border: '#166534', dot: '#4ade80' },
  idle:   { bg: '#1a1d27', border: '#2d3148', dot: '#475569' },
  error:  { bg: '#1f0a0a', border: '#7f1d1d', dot: '#f87171' },
}

const AGENT_COLORS = {
  laxmi: { bg: '#071a10', border: '#166534', accent: '#4ade80', light: '#86efac', dim: '#14532d', avatar: '🌿' },
  meera: { bg: '#071228', border: '#1d4ed8', accent: '#60a5fa', light: '#93c5fd', dim: '#1e3a8a', avatar: '🌊' },
  tara:  { bg: '#120a28', border: '#7c3aed', accent: '#a78bfa', light: '#c4b5fd', dim: '#4c1d95', avatar: '✨' },
}

const SENTIMENT_COLORS = {
  positive: '#4ade80',
  neutral: '#fbbf24',
  negative: '#f87171',
}

const MOAT_COLORS = {
  'switching cost': '#6366f1',
  'network effect': '#8b5cf6',
  'cost advantage': '#3b82f6',
  'intangible': '#06b6d4',
  'commodity': '#94a3b8',
}

function marketCapColor(cr) {
  if (!cr) return '#94a3b8'
  if (cr < 300) return '#4ade80'
  if (cr < 1000) return '#fbbf24'
  return '#fb923c'
}

function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1) return 'just now'
  if (diff < 60) return `${diff}m ago`
  const h = Math.floor(diff / 60)
  return `${h}h ${diff % 60}m ago`
}

function VerdictBadge({ verdict, size = 'sm' }) {
  const c = VERDICT_COLORS[verdict] || VERDICT_COLORS.unknown
  const pad = size === 'lg' ? '6px 14px' : '3px 9px'
  const fs = size === 'lg' ? '13px' : '11px'
  const icons = { shortlisted: '✅', borderline: '⚠️', rejected: '❌' }
  return (
    <span style={{
      padding: pad, borderRadius: '10px', fontSize: fs, fontWeight: 700,
      background: c.badge, color: c.text, border: `1px solid ${c.border}`,
      letterSpacing: '0.5px',
    }}>
      {icons[verdict] || ''} {verdict?.toUpperCase() || 'UNKNOWN'}
    </span>
  )
}

function AgentStatusDot({ status }) {
  const c = AGENT_STATUS_COLORS[status] || AGENT_STATUS_COLORS.idle
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: c.dot, marginRight: 6,
    }} />
  )
}

function TrendArrow({ trend }) {
  if (!trend) return <span style={{ color: '#475569' }}>→</span>
  if (trend === 'improving') return <span style={{ color: '#4ade80' }}>↑</span>
  if (trend === 'deteriorating' || trend.includes('deteriorating')) return <span style={{ color: '#f87171' }}>↓</span>
  return <span style={{ color: '#fbbf24' }}>→</span>
}

function MetricRow({ label, value, sub, color, trend }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
      <span style={{ fontSize: '12px', color: '#64748b' }}>{label}</span>
      <span style={{ fontSize: '13px', fontWeight: 600, color: color || '#e2e8f0', display: 'flex', alignItems: 'center', gap: 4 }}>
        {trend && <TrendArrow trend={trend} />}
        {value ?? '—'}
        {sub && <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 400, marginLeft: 2 }}>{sub}</span>}
      </span>
    </div>
  )
}

function SectionHeader({ children, icon }) {
  return (
    <div style={{
      fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase',
      letterSpacing: '1.2px', marginTop: '20px', marginBottom: '10px',
      display: 'flex', alignItems: 'center', gap: 6,
    }}>
      {icon && <span>{icon}</span>}
      {children}
    </div>
  )
}

function Panel({ children, accent }) {
  return (
    <div style={{
      background: '#1a1d27', borderRadius: '10px',
      border: `1px solid ${accent || '#2d3148'}`,
      padding: '14px', marginBottom: '12px',
    }}>
      {children}
    </div>
  )
}

function ScoreBadge({ score, max = 10 }) {
  if (score == null) return <span style={{ color: '#475569' }}>—</span>
  const pct = score / max
  const color = pct >= 0.7 ? '#4ade80' : pct >= 0.5 ? '#fbbf24' : '#f87171'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: '#0f1117', borderRadius: '6px', padding: '2px 8px',
    }}>
      <span style={{ fontSize: '15px', fontWeight: 700, color }}>{score}</span>
      <span style={{ fontSize: '11px', color: '#475569' }}>/{max}</span>
    </span>
  )
}

function OptionalityScore({ score }) {
  if (score == null) return null
  const color = score >= 8 ? '#4ade80' : score >= 5 ? '#fbbf24' : '#f87171'
  const label = score >= 8 ? 'CONVICTION BUY' : score >= 5 ? 'WATCH CLOSELY' : 'AVOID'
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      background: '#0f1117', borderRadius: '12px', padding: '12px 20px', marginBottom: '12px',
    }}>
      <div style={{ fontSize: '36px', fontWeight: 800, color, lineHeight: 1 }}>{score}</div>
      <div style={{ fontSize: '10px', color: '#475569', marginTop: '2px' }}>OUT OF 10</div>
      <div style={{
        marginTop: '6px', padding: '3px 10px', borderRadius: '8px', fontSize: '10px', fontWeight: 700,
        background: color + '20', color, border: `1px solid ${color}40`,
      }}>{label}</div>
    </div>
  )
}

function InventorySparkline({ days, trend }) {
  if (!days || days.length === 0) return null
  const max = Math.max(...days)
  const min = Math.min(...days)
  const range = max - min || 1
  const w = 60, h = 24
  const pts = days.map((v, i) => {
    const x = (i / (days.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  }).join(' ')
  const color = trend === 'improving' ? '#4ade80' : trend === 'deteriorating' ? '#f87171' : '#fbbf24'
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

function ContrарianFlag({ data }) {
  if (!data?.is_contrarian_signal) return null
  return (
    <div style={{
      background: '#1c0a3e', border: '1px solid #7c3aed', borderRadius: '8px',
      padding: '10px 12px', marginBottom: '12px', display: 'flex', gap: 8, alignItems: 'flex-start',
    }}>
      <span style={{ fontSize: '18px' }}>⚡</span>
      <div>
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#a78bfa', marginBottom: '2px' }}>
          CONTRARIAN SIGNAL — DOWN {Math.abs(data.down_pct_from_high)}% WHILE BUILDING
        </div>
        <div style={{ fontSize: '11px', color: '#7c3aed' }}>
          Market is penalising short-term pain. Capability building is underway. This is the setup.
        </div>
      </div>
    </div>
  )
}

// ─── Kanban Components ───────────────────────────────────────────────────────

function Spinner() {
  const [frame, setFrame] = useState(0)
  const frames = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
  useEffect(() => {
    const id = setInterval(() => setFrame(f => (f + 1) % frames.length), 100)
    return () => clearInterval(id)
  }, [])
  return <span style={{ fontFamily: 'monospace', fontSize: '13px' }}>{frames[frame]}</span>
}

function MarketCapBadge({ cr }) {
  const color = marketCapColor(cr)
  if (!cr) return null
  return (
    <span style={{
      fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '6px',
      background: color + '18', color, border: `1px solid ${color}40`,
    }}>
      ₹{cr >= 1000 ? `${(cr / 100).toFixed(0)}Cr` : `${cr}Cr`}
    </span>
  )
}

function KanbanCard({ item, agentName, agentStatus, isDone }) {
  const ac = agentName ? AGENT_COLORS[agentName] : null
  const isActive = agentStatus === 'analyzing'

  return (
    <div style={{
      background: '#1a1d27',
      border: `1px solid ${isDone ? '#2d3148' : ac ? ac.border : '#2d3148'}`,
      borderRadius: '10px',
      padding: '12px',
      marginBottom: '8px',
      cursor: 'default',
      boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
      borderLeft: `3px solid ${isDone ? '#2d3148' : ac ? ac.accent : '#475569'}`,
      transition: 'transform 0.1s, box-shadow 0.1s',
      userSelect: 'none',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.transform = 'translateY(-1px)'
      e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.4)'
    }}
    onMouseLeave={e => {
      e.currentTarget.style.transform = 'translateY(0)'
      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)'
    }}
    >
      {/* Symbol + market cap */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontFamily: 'monospace', fontSize: '13px', fontWeight: 800, color: '#e2e8f0', letterSpacing: '0.5px' }}>
          {item.symbol}
        </span>
        <MarketCapBadge cr={item.market_cap_cr} />
      </div>

      {/* Company name */}
      <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px', lineHeight: 1.3 }}>
        {item.company || item.symbol}
      </div>

      {/* Agent status row */}
      {agentName && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '5px 8px', borderRadius: '6px',
          background: ac ? ac.bg : '#0f1117',
          border: `1px solid ${ac ? ac.dim : '#1e293b'}`,
          marginBottom: isDone ? '8px' : 0,
        }}>
          <span style={{ fontSize: '12px' }}>{ac?.avatar}</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: ac ? ac.accent : '#94a3b8' }}>
            {agentName.charAt(0).toUpperCase() + agentName.slice(1)}
          </span>
          <span style={{ marginLeft: 'auto' }}>
            {isActive ? <Spinner /> : <span style={{ color: ac ? ac.accent : '#94a3b8', fontSize: '13px' }}>✓</span>}
          </span>
        </div>
      )}

      {/* Debate: all agents done */}
      {!agentName && item.agents_done && (
        <div style={{ display: 'flex', gap: 4, marginBottom: '4px' }}>
          {['laxmi','meera','tara'].map(a => {
            const done = item.agents_done?.includes(a)
            const c = AGENT_COLORS[a]
            return (
              <span key={a} style={{
                fontSize: '10px', padding: '2px 6px', borderRadius: '5px',
                background: done ? c.bg : '#0f1117',
                border: `1px solid ${done ? c.border : '#1e293b'}`,
                color: done ? c.accent : '#334155',
              }}>
                {c.avatar} {a}
              </span>
            )
          })}
        </div>
      )}

      {/* Done verdict */}
      {isDone && item.verdict && (
        <div style={{ marginTop: '4px' }}>
          <VerdictBadge verdict={item.verdict} />
          {item.reason && (
            <div style={{
              marginTop: '6px', fontSize: '10px', color: '#64748b',
              lineHeight: 1.4, fontStyle: 'italic',
              display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {item.reason}
            </div>
          )}
        </div>
      )}

      {/* Time */}
      {item.started_at && (
        <div style={{ fontSize: '10px', color: '#334155', marginTop: '6px' }}>
          {formatTime(item.started_at)}
        </div>
      )}
      {item.completed_at && (
        <div style={{ fontSize: '10px', color: '#334155', marginTop: '6px' }}>
          {formatTime(item.completed_at)}
        </div>
      )}
    </div>
  )
}

function KanbanColumn({ title, icon, cards, color, emptyText }) {
  return (
    <div className="kanban-column" style={{
      flex: '0 0 200px',
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Column header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 10px', marginBottom: '10px',
        background: '#141720', borderRadius: '8px',
        border: `1px solid ${color || '#2d3148'}`,
      }}>
        <span style={{ fontSize: '14px' }}>{icon}</span>
        <span style={{ fontSize: '11px', fontWeight: 700, color: color || '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          {title}
        </span>
        <span style={{
          marginLeft: 'auto', fontSize: '10px', fontWeight: 700,
          background: (color || '#475569') + '20', color: color || '#475569',
          border: `1px solid ${(color || '#475569') + '40'}`,
          borderRadius: '10px', padding: '1px 7px',
        }}>
          {cards.length}
        </span>
      </div>

      {/* Cards */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {cards.length === 0 ? (
          <div style={{
            padding: '16px 10px', textAlign: 'center', fontSize: '11px',
            color: '#334155', borderRadius: '8px', border: '1px dashed #1e293b',
          }}>
            {emptyText || 'Empty'}
          </div>
        ) : (
          cards.map((card, i) => card)
        )}
      </div>
    </div>
  )
}

function AgentCard({ name, info }) {
  const c = AGENT_COLORS[name]
  const isActive = info?.status === 'analyzing'
  const isDebating = info?.status === 'debating'
  const statusLabel = isActive ? 'Analyzing' : isDebating ? 'Debating' : 'Idle'
  const statusColor = isActive ? c.accent : isDebating ? '#fbbf24' : '#475569'

  return (
    <div style={{
      background: isActive ? c.bg : '#141720',
      border: `1px solid ${isActive ? c.border : '#2d3148'}`,
      borderRadius: '12px',
      padding: '14px 16px',
      flex: 1,
      minWidth: 0,
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '10px' }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: c.dim, border: `2px solid ${c.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '18px', flexShrink: 0,
        }}>
          {c.avatar}
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: c.accent }}>
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', background: statusColor,
              display: 'inline-block',
              boxShadow: isActive ? `0 0 8px ${statusColor}` : 'none',
            }} />
            <span style={{ fontSize: '11px', color: statusColor, fontWeight: 600 }}>
              {statusLabel}
            </span>
          </div>
        </div>
        {isActive && (
          <div style={{ marginLeft: 'auto' }}>
            <Spinner />
          </div>
        )}
      </div>

      {info?.current ? (
        <div style={{
          padding: '8px 10px', borderRadius: '8px',
          background: '#0f1117', border: `1px solid ${c.dim}`,
          marginBottom: '8px',
        }}>
          <div style={{ fontSize: '10px', color: '#475569', marginBottom: '3px' }}>CURRENT</div>
          <div style={{ fontFamily: 'monospace', fontSize: '13px', fontWeight: 700, color: '#e2e8f0' }}>
            {info.current}
          </div>
          {info.current_company && (
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
              {info.current_company}
            </div>
          )}
          {info.current_market_cap_cr && (
            <div style={{ marginTop: '5px' }}>
              <MarketCapBadge cr={info.current_market_cap_cr} />
            </div>
          )}
          {info.started_at && (
            <div style={{ fontSize: '10px', color: '#334155', marginTop: '5px' }}>
              {formatTime(info.started_at)}
            </div>
          )}
        </div>
      ) : (
        <div style={{
          padding: '8px 10px', borderRadius: '8px',
          background: '#0f1117', border: '1px solid #1e293b',
          marginBottom: '8px', fontSize: '11px', color: '#334155', fontStyle: 'italic',
        }}>
          Waiting for next company…
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
        <span>Today</span>
        <span style={{ color: c.accent, fontWeight: 700 }}>{info?.analyzed_today ?? 0} analyzed</span>
      </div>
    </div>
  )
}

function KanbanBoard({ progress }) {
  const agents = progress?.agents || { laxmi: {}, meera: {}, tara: {} }
  const queue = progress?.queue || []
  const inDebate = progress?.in_debate || []
  const recentCompleted = progress?.recent_completed?.slice(0, 10) || []

  // Build per-agent "analyzing" columns
  const agentColumns = ['laxmi', 'meera', 'tara'].map(name => {
    const info = agents[name] || {}
    const cards = []
    if (info.current) {
      cards.push({
        symbol: info.current,
        company: info.current_company,
        market_cap_cr: info.current_market_cap_cr,
        started_at: info.started_at,
      })
    }
    return { name, info, cards }
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Agent status sidebar (horizontal row) */}
      <div className="kanban-agent-row" style={{
        display: 'flex', gap: '12px', padding: '0 0 16px',
        flexShrink: 0,
      }}>
        {['laxmi', 'meera', 'tara'].map(name => (
          <AgentCard key={name} name={name} info={agents[name]} />
        ))}
      </div>

      {/* Board */}
      <div className="kanban-board" style={{
        flex: 1,
        display: 'flex',
        gap: '12px',
        overflow: 'auto',
        paddingBottom: '8px',
      }}>
        {/* Queue */}
        <KanbanColumn
          title="Queue"
          icon="📋"
          color="#6366f1"
          emptyText="No companies queued"
          cards={queue.map((item, i) => (
            <KanbanCard key={item.symbol + i} item={item} />
          ))}
        />

        {/* Per-agent analyzing columns */}
        {agentColumns.map(({ name, info, cards }) => {
          const c = AGENT_COLORS[name]
          const labels = { laxmi: 'Laxmi Analyzing', meera: 'Meera Analyzing', tara: 'Tara Analyzing' }
          return (
            <KanbanColumn
              key={name}
              title={labels[name]}
              icon={c.avatar}
              color={c.accent}
              emptyText="Idle"
              cards={cards.map((item, i) => (
                <KanbanCard
                  key={item.symbol + i}
                  item={item}
                  agentName={name}
                  agentStatus={info.status}
                />
              ))}
            />
          )
        })}

        {/* In Debate */}
        <KanbanColumn
          title="In Debate"
          icon="⚔️"
          color="#fbbf24"
          emptyText="No debates active"
          cards={inDebate.map((item, i) => (
            <KanbanCard key={item.symbol + i} item={item} />
          ))}
        />

        {/* Done */}
        <KanbanColumn
          title="Done"
          icon="✅"
          color="#4ade80"
          emptyText="No completed companies yet"
          cards={recentCompleted.map((item, i) => (
            <KanbanCard key={item.symbol + i} item={item} isDone />
          ))}
        />
      </div>
    </div>
  )
}

// ─── Detail Panel ────────────────────────────────────────────────────────────

function CompanyDetailPanel({ data, onClose, isMobile }) {
  const vc = VERDICT_COLORS[data.verdict] || VERDICT_COLORS.unknown
  const opt = data.optionality
  const laxmi = data.laxmi || {}
  const meera = data.meera || {}
  const tara = data.tara || {}

  const lastInventoryDay = laxmi.inventory_days?.[laxmi.inventory_days.length - 1]
  const lastReceivableDay = laxmi.receivable_days?.[laxmi.receivable_days.length - 1]

  return (
    <div className="detail-panel" style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: isMobile ? '100%' : '500px',
      background: '#0f1117', borderLeft: '1px solid #2d3148',
      display: 'flex', flexDirection: 'column', zIndex: 100,
      boxShadow: '-12px 0 48px rgba(0,0,0,0.6)',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 20px 16px', borderBottom: '1px solid #2d3148', flexShrink: 0,
        background: vc.bg, borderTop: `3px solid ${vc.border}`,
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: '16px', right: '16px',
            background: '#1a1d27', border: '1px solid #2d3148', color: '#94a3b8',
            cursor: 'pointer', fontSize: '16px', borderRadius: '6px', width: '28px', height: '28px',
          }}
        >✕</button>
        <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#64748b', marginBottom: '3px' }}>
          {data.symbol} · {data.sector}
        </div>
        <div style={{ fontSize: '22px', fontWeight: 800, color: '#f1f5f9', marginBottom: '4px', lineHeight: 1.2 }}>
          {data.name}
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap' }}>
          <VerdictBadge verdict={data.verdict} size="lg" />
          {data.market_cap && (
            <span style={{ fontSize: '13px', color: '#94a3b8' }}>
              Market Cap: <strong style={{ color: '#e2e8f0' }}>{data.market_cap}</strong>
            </span>
          )}
          {opt?.score != null && (
            <span style={{
              fontSize: '11px', padding: '2px 8px', borderRadius: '8px',
              background: '#1c0a3e', border: '1px solid #7c3aed', color: '#a78bfa',
            }}>
              Optionality: {opt.score}/10
            </span>
          )}
        </div>
        {data.description && (
          <div style={{
            fontSize: '12px', color: '#94a3b8', lineHeight: 1.6,
            background: '#0f1117', borderRadius: '8px', padding: '10px 12px',
          }}>
            {data.description}
          </div>
        )}
        {data.screener_url && (
          <div style={{ marginTop: '8px' }}>
            <a
              href={data.screener_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: '11px', color: '#6366f1', textDecoration: 'none' }}
            >
              → View on Screener.in ↗
            </a>
          </div>
        )}
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

        {/* Investment thesis */}
        {data.investment_thesis && (
          <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, padding: 12, marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, letterSpacing: 1 }}>INVESTMENT THESIS</div>
            <div style={{ fontSize: 14, color: '#e2e8f0', lineHeight: 1.6 }}>{data.investment_thesis}</div>
          </div>
        )}

        {/* Verdict memo */}
        {(data.verdict_reason || data.verdict_memo) && (
          <Panel accent={vc.border}>
            {data.verdict_reason && (
              <div style={{ fontSize: '12px', fontWeight: 700, color: vc.text, marginBottom: '6px' }}>
                {data.verdict_reason}
              </div>
            )}
            {data.verdict_memo && (
              <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
                {data.verdict_memo}
              </div>
            )}
          </Panel>
        )}

        {/* Contrarian flag */}
        {opt && <ContrарianFlag data={opt} />}

        {/* === OPTIONALITY SECTION === */}
        {opt && (
          <>
            <SectionHeader icon="⚡">Optionality & Capability Building</SectionHeader>
            <Panel accent="#4c1d95">
              <OptionalityScore score={opt.score} />

              <div style={{ marginBottom: '10px' }}>
                <div style={{ fontSize: '11px', color: '#7c3aed', fontWeight: 600, marginBottom: '6px' }}>
                  CAPABILITY BUILDING SIGNALS
                </div>
                {opt.capex_vs_depreciation != null && (
                  <MetricRow
                    label="Capex / Depreciation"
                    value={`${opt.capex_vs_depreciation}×`}
                    color={opt.capex_vs_depreciation >= 2 ? '#a78bfa' : '#94a3b8'}
                  />
                )}
                {opt.rd_pct_revenue != null && (
                  <MetricRow
                    label="R&D % of Revenue"
                    value={`${opt.rd_pct_revenue}%`}
                    trend={opt.rd_trend === 'growing' ? 'improving' : 'stable'}
                  />
                )}
                {opt.new_geographies?.length > 0 && (
                  <div style={{ padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
                    <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '3px' }}>New Geographies</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {opt.new_geographies.map(g => (
                        <span key={g} style={{
                          fontSize: '10px', padding: '2px 7px', borderRadius: '6px',
                          background: '#1e1b4b', color: '#818cf8', border: '1px solid #3730a3',
                        }}>{g}</span>
                      ))}
                    </div>
                  </div>
                )}
                {opt.new_product_categories?.length > 0 && (
                  <div style={{ padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
                    <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '3px' }}>New Product Categories</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {opt.new_product_categories.map(p => (
                        <span key={p} style={{
                          fontSize: '10px', padding: '2px 7px', borderRadius: '6px',
                          background: '#0c1a2e', color: '#38bdf8', border: '1px solid #0369a1',
                        }}>{p}</span>
                      ))}
                    </div>
                  </div>
                )}
                {opt.talent_buildup != null && (
                  <MetricRow
                    label="Talent Buildup"
                    value={opt.talent_buildup ? 'Yes — hiring from competitors' : 'No signal'}
                    color={opt.talent_buildup ? '#4ade80' : '#94a3b8'}
                  />
                )}
              </div>

              {opt.worst_case && (
                <div style={{
                  background: '#1f0a0a', border: '1px solid #450a0a', borderRadius: '8px',
                  padding: '10px', marginBottom: '8px',
                }}>
                  <div style={{ fontSize: '10px', color: '#f87171', fontWeight: 700, marginBottom: '4px' }}>
                    ▼ WORST CASE (LIMITED DOWNSIDE)
                  </div>
                  <div style={{ fontSize: '11px', color: '#fca5a5', lineHeight: 1.5 }}>{opt.worst_case}</div>
                </div>
              )}
              {opt.best_case_optionality && (
                <div style={{
                  background: '#052e16', border: '1px solid #14532d', borderRadius: '8px',
                  padding: '10px', marginBottom: '8px',
                }}>
                  <div style={{ fontSize: '10px', color: '#4ade80', fontWeight: 700, marginBottom: '4px' }}>
                    ▲ BEST CASE OPTIONALITY (ASYMMETRIC UPSIDE)
                  </div>
                  <div style={{ fontSize: '11px', color: '#86efac', lineHeight: 1.5 }}>{opt.best_case_optionality}</div>
                </div>
              )}
              {opt.archetype && (
                <div style={{
                  background: '#1c1a07', border: '1px solid #451a03', borderRadius: '8px',
                  padding: '10px',
                }}>
                  <div style={{ fontSize: '10px', color: '#fbbf24', fontWeight: 700, marginBottom: '4px' }}>
                    💡 ARCHETYPE COMPARISON
                  </div>
                  <div style={{ fontSize: '11px', color: '#fde68a', lineHeight: 1.5 }}>{opt.archetype}</div>
                </div>
              )}
            </Panel>
          </>
        )}

        {/* === FUNDAMENTAL PANEL === */}
        <SectionHeader icon="📊">Fundamentals — Laxmi</SectionHeader>
        <Panel>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', color: '#64748b' }}>Overall Score</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <ScoreBadge score={laxmi.score} />
              {(() => {
                const laxmiPass = ['pass', 'shortlist', 'shortlisted'].includes(laxmi.verdict?.toLowerCase())
                return (
                  <span style={{ fontSize: '11px', fontWeight: 600, color: laxmiPass ? '#4ade80' : '#f87171' }}>
                    {laxmiPass ? '✓ PASS' : '✗ FAIL'}
                  </span>
                )
              })()}
            </div>
          </div>

          <MetricRow label="FCF Positive Years" value={laxmi.fcf_positive_years} />
          <MetricRow
            label="ROCE (5yr avg)"
            value={laxmi.roce_5yr_avg ? `${laxmi.roce_5yr_avg}%` : null}
            color={laxmi.roce_5yr_avg >= 20 ? '#4ade80' : laxmi.roce_5yr_avg >= 15 ? '#fbbf24' : '#f87171'}
          />
          <MetricRow
            label="Debt / Equity"
            value={laxmi.debt_equity}
            color={
              typeof laxmi.debt_equity === 'number'
                ? laxmi.debt_equity <= 0.5 ? '#4ade80' : laxmi.debt_equity <= 1.0 ? '#fbbf24' : '#f87171'
                : '#94a3b8'
            }
          />
          <MetricRow label="Promoter Holding" value={laxmi.promoter_holding ? `${laxmi.promoter_holding}%` : null} />
          <MetricRow
            label="Promoter Pledging"
            value={laxmi.promoter_pledge_pct != null ? `${laxmi.promoter_pledge_pct}%` : null}
            color={
              laxmi.promoter_pledge_pct === 0 ? '#4ade80'
                : laxmi.promoter_pledge_pct <= 10 ? '#fbbf24'
                : '#f87171'
            }
          />
          <MetricRow
            label="Owner Earnings"
            value={laxmi.owner_earnings_cr != null ? `₹${laxmi.owner_earnings_cr} Cr` : null}
            color={laxmi.owner_earnings_cr > 0 ? '#4ade80' : '#f87171'}
          />
          <MetricRow
            label="Auditor Changed"
            value={laxmi.auditor_changed === true ? 'Yes ⚠' : laxmi.auditor_changed === false ? 'No' : null}
            color={laxmi.auditor_changed ? '#f87171' : '#4ade80'}
          />
          <MetricRow
            label="RPT % of Revenue"
            value={laxmi.rpt_pct_revenue ? `${laxmi.rpt_pct_revenue}%` : null}
            color={laxmi.rpt_pct_revenue > 10 ? '#f87171' : laxmi.rpt_pct_revenue > 5 ? '#fbbf24' : '#4ade80'}
          />

          <div style={{
            marginTop: '12px', padding: '10px', background: '#0f1117',
            borderRadius: '8px', border: '1px solid #1e293b',
          }}>
            <div style={{ fontSize: '10px', color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
              Working Capital & CCC
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <div style={{ flex: 1, background: '#1a1d27', borderRadius: '6px', padding: '8px' }}>
                <div style={{ fontSize: '10px', color: '#475569', marginBottom: '4px' }}>Inventory Days</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <TrendArrow trend={laxmi.inventory_days_trend} />
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#e2e8f0' }}>
                    {lastInventoryDay ?? '—'}
                  </span>
                </div>
                <InventorySparkline days={laxmi.inventory_days} trend={laxmi.inventory_days_trend} />
              </div>

              <div style={{ flex: 1, background: '#1a1d27', borderRadius: '6px', padding: '8px' }}>
                <div style={{ fontSize: '10px', color: '#475569', marginBottom: '4px' }}>Receivable Days</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <TrendArrow trend={laxmi.receivable_days_trend} />
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#e2e8f0' }}>
                    {lastReceivableDay ?? '—'}
                  </span>
                </div>
                <InventorySparkline days={laxmi.receivable_days} trend={laxmi.receivable_days_trend} />
              </div>

              <div style={{ flex: 1, background: '#1a1d27', borderRadius: '6px', padding: '8px' }}>
                <div style={{ fontSize: '10px', color: '#475569', marginBottom: '4px' }}>Payable Days</div>
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#e2e8f0' }}>
                  {laxmi.payable_days_current ?? '—'}
                </span>
              </div>
            </div>

            {laxmi.cash_conversion_cycle != null && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: '#1a1d27', borderRadius: '6px', padding: '8px 10px',
              }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>
                  Cash Conversion Cycle
                  <span style={{ fontSize: '10px', color: '#475569', marginLeft: '4px' }}>
                    (Inv + Rec - Pay)
                  </span>
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <TrendArrow trend={laxmi.ccc_trend} />
                  <span style={{
                    fontSize: '15px', fontWeight: 800,
                    color: laxmi.ccc_trend === 'improving' ? '#4ade80'
                      : laxmi.ccc_trend?.includes('deteriorating') ? '#f87171' : '#fbbf24',
                  }}>
                    {laxmi.cash_conversion_cycle}d
                  </span>
                </span>
              </div>
            )}
          </div>

          {laxmi.key_strengths?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {laxmi.key_strengths.map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: '#34d399', padding: '2px 0' }}>✓ {s}</div>
              ))}
            </div>
          )}
          {laxmi.key_risks?.length > 0 && (
            <div style={{ marginTop: 4 }}>
              {laxmi.key_risks.map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: '#f87171', padding: '2px 0' }}>⚠ {r}</div>
              ))}
            </div>
          )}

          {laxmi.notes && (
            <div style={{ marginTop: '10px', fontSize: '11px', color: '#64748b', lineHeight: 1.5, fontStyle: 'italic' }}>
              {laxmi.notes}
            </div>
          )}
        </Panel>

        {/* === TECHNICAL PANEL === */}
        <SectionHeader icon="📈">Technical & Market — Meera</SectionHeader>
        <Panel>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', color: '#64748b' }}>Overall Score</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <ScoreBadge score={meera.score} />
              {(() => {
                const meeraPass = ['pass', 'shortlist', 'shortlisted'].includes(meera.verdict?.toLowerCase())
                return (
                  <span style={{ fontSize: '11px', fontWeight: 600, color: meeraPass ? '#4ade80' : '#f87171' }}>
                    {meeraPass ? '✓ PASS' : '✗ FAIL'}
                  </span>
                )
              })()}
            </div>
          </div>

          {meera.week52_from_high_pct != null && (
            <MetricRow
              label="vs 52-Week High"
              value={`${meera.week52_from_high_pct}%`}
              color={meera.week52_from_high_pct > -15 ? '#4ade80' : meera.week52_from_high_pct > -40 ? '#fbbf24' : '#f87171'}
            />
          )}
          {meera.week52_from_low_pct != null && (
            <MetricRow
              label="vs 52-Week Low"
              value={`+${meera.week52_from_low_pct}%`}
              color={meera.week52_from_low_pct > 30 ? '#4ade80' : '#94a3b8'}
            />
          )}
          {meera.vs_3yr_high_pct != null && (
            <MetricRow
              label="vs 3-Year High"
              value={`${meera.vs_3yr_high_pct}%`}
              color={meera.vs_3yr_high_pct > -20 ? '#4ade80' : meera.vs_3yr_high_pct > -50 ? '#fbbf24' : '#f87171'}
            />
          )}
          {meera.revenue_yoy_growth != null && (
            <MetricRow
              label="Revenue YoY Growth"
              value={`${meera.revenue_yoy_growth > 0 ? '+' : ''}${meera.revenue_yoy_growth}%`}
              color={meera.revenue_yoy_growth >= 20 ? '#4ade80' : meera.revenue_yoy_growth >= 0 ? '#fbbf24' : '#f87171'}
            />
          )}
          {meera.relative_strength_vs_smallcap && (
            <MetricRow
              label="vs Nifty Smallcap 250"
              value={meera.relative_strength_vs_smallcap}
              color={
                meera.relative_strength_vs_smallcap?.includes('outperform') ? '#4ade80'
                  : meera.relative_strength_vs_smallcap?.includes('underperform') ? '#f87171' : '#fbbf24'
              }
            />
          )}
          {meera.delivery_pct != null && (
            <MetricRow
              label="Delivery %"
              value={`${meera.delivery_pct}%`}
              color={meera.delivery_pct >= 60 ? '#4ade80' : meera.delivery_pct >= 40 ? '#fbbf24' : '#f87171'}
            />
          )}
          {meera.promoter_buying != null && (
            <MetricRow
              label="Promoter Open-Market Buying"
              value={meera.promoter_buying ? '✓ Yes' : 'No'}
              color={meera.promoter_buying ? '#4ade80' : '#94a3b8'}
            />
          )}

          {meera.revenue_growth_pct != null && (
            <MetricRow
              label="Revenue Growth (YoY)"
              value={`${meera.revenue_growth_pct > 0 ? '+' : ''}${meera.revenue_growth_pct}%`}
              color={meera.revenue_growth_pct >= 20 ? '#4ade80' : meera.revenue_growth_pct >= 0 ? '#fbbf24' : '#f87171'}
            />
          )}
          {meera.pe_ratio != null && (
            <MetricRow label="PE Ratio" value={meera.pe_ratio} />
          )}

          {meera.optionality_signals?.length > 0 && (
            <div style={{ background: '#451a03', border: '1px solid #d97706', borderRadius: 6, padding: 8, marginTop: 8 }}>
              <div style={{ fontSize: 11, color: '#fbbf24', marginBottom: 4, fontWeight: 700 }}>⚡ OPTIONALITY SIGNALS</div>
              {meera.optionality_signals.map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: '#fcd34d', padding: '1px 0' }}>• {s}</div>
              ))}
            </div>
          )}

          {meera.notes && (
            <div style={{ marginTop: '10px', fontSize: '11px', color: '#64748b', lineHeight: 1.5, fontStyle: 'italic' }}>
              {meera.notes}
            </div>
          )}
        </Panel>

        {/* === STORY PANEL === */}
        <SectionHeader icon="📖">Story & Qualitative — Tara</SectionHeader>
        <Panel>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', color: '#64748b' }}>Overall Score</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <ScoreBadge score={tara.score} />
              {(() => {
                const taraPass = ['pass', 'shortlist', 'shortlisted'].includes(tara.verdict?.toLowerCase())
                return (
                  <span style={{ fontSize: '11px', fontWeight: 600, color: taraPass ? '#4ade80' : '#f87171' }}>
                    {taraPass ? '✓ PASS' : '✗ FAIL'}
                  </span>
                )
              })()}
            </div>
          </div>

          {tara.moat_type && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
              <span style={{ fontSize: '12px', color: '#64748b' }}>Business Moat</span>
              <span style={{
                fontSize: '11px', padding: '2px 8px', borderRadius: '6px', fontWeight: 600,
                background: (MOAT_COLORS[tara.moat_type] || '#475569') + '20',
                color: MOAT_COLORS[tara.moat_type] || '#94a3b8',
                border: `1px solid ${(MOAT_COLORS[tara.moat_type] || '#475569') + '40'}`,
              }}>
                {tara.moat_type.toUpperCase()}
              </span>
            </div>
          )}
          {tara.management_quality_score != null && (
            <MetricRow
              label="Management Quality"
              value={`${tara.management_quality_score}/10`}
              color={tara.management_quality_score >= 7 ? '#4ade80' : tara.management_quality_score >= 5 ? '#fbbf24' : '#f87171'}
            />
          )}
          {tara.guidance_track_record && (
            <div style={{ padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
              <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '2px' }}>Guidance Track Record</div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>{tara.guidance_track_record}</div>
            </div>
          )}
          {tara.news_sentiment && (
            <MetricRow
              label="News Sentiment"
              value={tara.news_sentiment.charAt(0).toUpperCase() + tara.news_sentiment.slice(1)}
              color={SENTIMENT_COLORS[tara.news_sentiment] || '#94a3b8'}
            />
          )}
          {tara.key_risk && (
            <div style={{
              marginTop: '10px', padding: '8px 10px',
              background: '#1f0a0a', border: '1px solid #450a0a', borderRadius: '6px',
            }}>
              <div style={{ fontSize: '10px', color: '#f87171', fontWeight: 700, marginBottom: '3px' }}>KEY RISK</div>
              <div style={{ fontSize: '11px', color: '#fca5a5', lineHeight: 1.5 }}>{tara.key_risk}</div>
            </div>
          )}

          {tara.smile_score != null && (
            <MetricRow
              label="SMILE Score (Kedia)"
              value={`${tara.smile_score}/3`}
              color={tara.smile_score >= 2 ? '#4ade80' : tara.smile_score >= 1 ? '#fbbf24' : '#94a3b8'}
            />
          )}

          {tara.taleb_signals?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>Taleb Signals</div>
              {tara.taleb_signals.map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: '#60a5fa', padding: '1px 0' }}>◆ {s}</div>
              ))}
            </div>
          )}

          {tara.contrarian_angle && (
            <div style={{ background: '#0f2027', border: '1px solid #0e7490', borderRadius: 6, padding: 8, marginTop: 8 }}>
              <span style={{ color: '#22d3ee', fontSize: 12 }}>🎯 Contrarian: {tara.contrarian_angle}</span>
            </div>
          )}

          {tara.notes && (
            <div style={{ marginTop: '10px', fontSize: '11px', color: '#64748b', lineHeight: 1.5, fontStyle: 'italic' }}>
              {tara.notes}
            </div>
          )}
        </Panel>

        {/* === DEBATE REASONING === */}
        {data.debate_reasoning?.length > 0 && (
          <div style={{ marginTop: 20, background: '#1a1f2e', borderRadius: 8, padding: 16 }}>
            <div style={{ fontSize: 11, letterSpacing: 2, color: '#6b7280', marginBottom: 12 }}>
              ⚖️ DEBATE REASONING
            </div>
            {data.debate_reasoning.map((line, i) => (
              <div key={i} style={{ fontSize: 13, color: '#d1d5db', padding: '4px 0', borderBottom: '1px solid #2d3748' }}>
                {line}
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '8px', fontSize: '11px', color: '#334155', textAlign: 'center' }}>
          Analyzed {data.analyzed_at ? new Date(data.analyzed_at).toLocaleString() : '—'}
        </div>
      </div>
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

const VIEW_TABS = ['All', 'Shortlisted', 'Borderline', 'Rejected', 'Task Board']

export default function App() {
  const [progress, setProgress] = useState(null)
  const [companies, setCompanies] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [selectedTab, setSelectedTab] = useState('All')
  const [selectedCompany, setSelectedCompany] = useState(null)
  const [companyDetail, setCompanyDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [loadingList, setLoadingList] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768)

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    let cancelled = false
    const doFetch = async () => {
      setLoadingList(true)
      try {
        const isBoard = selectedTab === 'Task Board'
        const verdictParam = (!isBoard && selectedTab !== 'All')
          ? `&verdict=${selectedTab.toLowerCase()}`
          : ''
        const [prog, comps] = await Promise.all([
          fetch(`${API}/progress`).then(r => r.json()),
          fetch(`${API}/companies?page=${page}&limit=50${verdictParam}`).then(r => r.json()),
        ])
        if (cancelled) return
        setProgress(prog)
        setCompanies(comps.companies || [])
        setTotalPages(comps.pages || 1)
        setLastUpdated(new Date())
        setError(null)
      } catch {
        if (!cancelled) setError('API unreachable — retrying...')
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    }
    doFetch()
    // Kanban auto-refreshes every 15s, table every 30s
    const id = setInterval(doFetch, selectedTab === 'Task Board' ? 15000 : 30000)
    return () => { cancelled = true; clearInterval(id) }
  }, [page, selectedTab])

  const openCompany = async (symbol) => {
    setSelectedCompany(symbol)
    setLoadingDetail(true)
    try {
      const data = await fetch(`${API}/company/${symbol}`).then(r => r.json())
      setCompanyDetail(data)
    } catch {
      setCompanyDetail(null)
    }
    setLoadingDetail(false)
  }

  const closePanel = () => { setSelectedCompany(null); setCompanyDetail(null) }

  const isKanban = selectedTab === 'Task Board'
  // Backend already paginates + filters by verdict, so render the page as-is.
  const filteredCompanies = isKanban ? [] : companies

  const tabCount = (t) => {
    if (t === 'All') return progress?.analyzed ?? 0
    return progress?.[t.toLowerCase()] ?? 0
  }

  const total = progress?.total || 1840
  const analyzed = progress?.analyzed || 0
  const pct = total > 0 ? Math.min(100, (analyzed / total) * 100) : 0
  const agents = progress?.agents || {
    laxmi: { status: 'idle', current: null },
    meera: { status: 'idle', current: null },
    tara: { status: 'idle', current: null },
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0f1117', color: '#e2e8f0', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Top bar */}
      <div className="top-bar" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', background: '#1a1d27', borderBottom: '1px solid #2d3148',
        flexShrink: 0,
      }}>
        <div>
          <div className="top-bar-title" style={{ fontSize: '18px', fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.5px' }}>
            Project Microcap Hunt
          </div>
          <div className="top-bar-subtitle" style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
            Automated multi-agent stock screening · NSE/BSE Microcaps · Taleb Optionality Framework
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {error && <span style={{ fontSize: '12px', color: '#f87171' }}>{error}</span>}
          <div className="top-bar-refresh" style={{
            padding: '4px 10px', background: '#1e293b', border: '1px solid #334155',
            borderRadius: '12px', fontSize: '11px', color: '#94a3b8',
          }}>
            Auto-refresh: {isKanban ? '15s' : '30s'} {lastUpdated ? `· ${lastUpdated.toLocaleTimeString()}` : ''}
          </div>
        </div>
      </div>

      <div className="app-body" style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar — hidden on kanban */}
        {!isKanban && (
          <div className="app-sidebar" style={{
            width: '220px', background: '#141720', borderRight: '1px solid #2d3148',
            padding: '16px', overflowY: 'auto', flexShrink: 0,
          }}>
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '10px', fontWeight: 600, color: '#475569', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '10px' }}>
                Agents
              </div>
              {Object.entries(agents).map(([name, info]) => {
                const sc = AGENT_STATUS_COLORS[info.status] || AGENT_STATUS_COLORS.idle
                return (
                  <div key={name} style={{
                    padding: '10px 12px', borderRadius: '8px', border: '1px solid',
                    marginBottom: '8px', background: sc.bg, borderColor: sc.border,
                  }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>
                      <AgentStatusDot status={info.status} />
                      {name.charAt(0).toUpperCase() + name.slice(1)}
                    </div>
                    <div style={{ fontSize: '11px', opacity: 0.7 }}>{info.status}</div>
                    {info.current && <div style={{ fontSize: '11px', marginTop: '4px' }}>→ {info.current}</div>}
                  </div>
                )
              })}
            </div>

            <div>
              <div style={{ fontSize: '10px', fontWeight: 600, color: '#475569', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '10px' }}>
                Session
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.8 }}>
                <div>Universe: <span style={{ color: '#94a3b8' }}>{total.toLocaleString()}</span></div>
                <div>Analyzed: <span style={{ color: '#94a3b8' }}>{analyzed.toLocaleString()}</span></div>
                <div>Remaining: <span style={{ color: '#94a3b8' }}>{(total - analyzed).toLocaleString()}</span></div>
              </div>
            </div>
          </div>
        )}

        {/* Main area */}
        <div className="main-area" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '20px' }}>
          {/* Stats — hidden on kanban */}
          {!isKanban && (
            <div className="stats-row" style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexShrink: 0 }}>
              {[
                { label: 'Total Universe', value: total.toLocaleString(), color: '#6366f1' },
                { label: 'Shortlisted', value: (progress?.shortlisted || 0).toString(), color: '#4ade80' },
                { label: 'Borderline', value: (progress?.borderline || 0).toString(), color: '#fbbf24' },
                { label: 'Rejected', value: (progress?.rejected || 0).toString(), color: '#f87171' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{
                  flex: 1, padding: '16px', background: '#1a1d27', border: '1px solid #2d3148',
                  borderRadius: '10px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1, color }}>{value}</div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Progress bar — hidden on kanban */}
          {!isKanban && (
            <div style={{ marginBottom: '20px', flexShrink: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                <span>Analysis Progress</span>
                <span>{analyzed.toLocaleString()} / {total.toLocaleString()} ({pct.toFixed(1)}%)</span>
              </div>
              <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', background: 'linear-gradient(90deg, #3b82f6, #6366f1)',
                  borderRadius: '4px', transition: 'width 0.5s ease', width: `${pct}%`,
                }} />
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="tab-bar" style={{ display: 'flex', gap: '4px', marginBottom: '16px', flexShrink: 0 }}>
            {VIEW_TABS.map(t => {
              const active = selectedTab === t
              const isBoard = t === 'Task Board'
              return (
                <button
                  key={t}
                  className="tab-btn"
                  onClick={() => { setSelectedTab(t); setPage(1) }}
                  style={{
                    padding: '7px 16px', borderRadius: '6px', cursor: 'pointer',
                    fontSize: '13px', fontWeight: 500, transition: 'all 0.15s',
                    background: active ? (isBoard ? '#7c3aed' : '#6366f1') : '#1a1d27',
                    color: active ? '#fff' : '#94a3b8',
                    border: `1px solid ${active ? (isBoard ? '#7c3aed' : '#6366f1') : '#2d3148'}`,
                  }}
                >
                  {isBoard ? '📋 ' : ''}{t}
                  {!isBoard && (
                    <span style={{ marginLeft: 6, opacity: 0.7, fontSize: '11px' }}>
                      ({tabCount(t).toLocaleString()})
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Content */}
          {isKanban ? (
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <KanbanBoard progress={progress} />
            </div>
          ) : (
            <div className="company-table-wrapper" style={{ flex: 1, overflow: 'auto', borderRadius: '10px', border: '1px solid #2d3148' }}>
              {loadingList ? (
                <div style={{ padding: '60px', textAlign: 'center' }}>
                  <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                  <div style={{ width: 32, height: 32, border: '3px solid #2d3148', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
                  <div style={{ color: '#475569', fontSize: '13px' }}>Loading companies...</div>
                </div>
              ) : filteredCompanies.length === 0 ? (
                <div style={{ padding: '60px', textAlign: 'center', color: '#475569', fontSize: '14px' }}>
                  No companies in this category yet.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {['Symbol', 'Name', 'Sector', 'Verdict', 'Optionality', 'Laxmi', 'Meera', 'Tara', 'Analyzed'].map(h => (
                        <th key={h} style={{
                          padding: '10px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 600,
                          color: '#64748b', letterSpacing: '0.5px', textTransform: 'uppercase',
                          background: '#141720', borderBottom: '1px solid #2d3148', position: 'sticky', top: 0,
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCompanies.map(c => {
                      const isSelected = selectedCompany === c.symbol
                      return (
                        <tr
                          key={c.symbol}
                          style={{
                            borderBottom: '1px solid #1e293b', cursor: 'pointer',
                            background: isSelected ? '#1e293b' : 'transparent',
                            transition: 'background 0.1s',
                          }}
                          onClick={() => openCompany(c.symbol)}
                          onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#1a1d27' }}
                          onMouseLeave={e => { e.currentTarget.style.background = isSelected ? '#1e293b' : 'transparent' }}
                        >
                          <td style={{ padding: '11px 14px', fontSize: '13px', fontWeight: 700, color: '#e2e8f0', fontFamily: 'monospace' }}>
                            {c.symbol}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '13px', color: '#cbd5e1', maxWidth: '180px' }}>
                            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</div>
                            {c.market_cap && <div style={{ fontSize: '10px', color: '#475569', marginTop: '1px' }}>{c.market_cap}</div>}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap' }}>
                            {c.sector || '—'}
                          </td>
                          <td style={{ padding: '11px 14px' }}>
                            <VerdictBadge verdict={c.verdict} />
                          </td>
                          <td style={{ padding: '11px 14px' }}>
                            {c.optionality_score != null ? (
                              <span style={{
                                fontSize: '13px', fontWeight: 700,
                                color: c.optionality_score >= 8 ? '#a78bfa' : c.optionality_score >= 5 ? '#fbbf24' : '#94a3b8',
                              }}>
                                {c.optionality_score}/10
                              </span>
                            ) : <span style={{ color: '#334155' }}>—</span>}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '12px' }}>
                            {c.laxmi_score != null ? (
                              <span style={{ color: c.laxmi_score >= 7 ? '#4ade80' : c.laxmi_score >= 5 ? '#fbbf24' : '#f87171' }}>
                                {c.laxmi_score}/10
                              </span>
                            ) : <span style={{ color: '#334155' }}>—</span>}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '12px' }}>
                            {c.meera_score != null ? (
                              <span style={{ color: c.meera_score >= 7 ? '#4ade80' : c.meera_score >= 5 ? '#fbbf24' : '#f87171' }}>
                                {c.meera_score}/10
                              </span>
                            ) : <span style={{ color: '#334155' }}>—</span>}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '12px' }}>
                            {c.tara_score != null ? (
                              <span style={{ color: c.tara_score >= 7 ? '#4ade80' : c.tara_score >= 5 ? '#fbbf24' : '#f87171' }}>
                                {c.tara_score}/10
                              </span>
                            ) : <span style={{ color: '#334155' }}>—</span>}
                          </td>
                          <td style={{ padding: '11px 14px', fontSize: '11px', color: '#475569' }}>
                            {c.analyzed_at ? new Date(c.analyzed_at).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Pagination controls */}
          {!isKanban && !loadingList && totalPages > 1 && (
            <div style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8,
              padding: '12px', borderTop: '1px solid #2d3148', flexShrink: 0,
            }}>
              <button
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                style={{
                  background: '#1a1d27', border: '1px solid #2d3148', color: '#94a3b8',
                  borderRadius: 6, padding: '6px 14px', fontSize: 13,
                  cursor: page === 1 ? 'not-allowed' : 'pointer',
                  opacity: page === 1 ? 0.4 : 1,
                }}
              >← Prev</button>
              <span style={{ color: '#94a3b8', fontSize: 13 }}>Page {page} of {totalPages}</span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                style={{
                  background: '#1a1d27', border: '1px solid #2d3148', color: '#94a3b8',
                  borderRadius: 6, padding: '6px 14px', fontSize: 13,
                  cursor: page === totalPages ? 'not-allowed' : 'pointer',
                  opacity: page === totalPages ? 0.4 : 1,
                }}
              >Next →</button>
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedCompany && (
        loadingDetail ? (
          <div className="detail-panel" style={{
            position: 'fixed', top: 0, right: 0, bottom: 0, width: isMobile ? '100%' : '500px',
            background: '#141720', borderLeft: '1px solid #2d3148', zIndex: 100,
            overflowY: 'auto', padding: '20px',
          }}>
            <style>{`
              @keyframes shimmer {
                0% { background-position: -400px 0; }
                100% { background-position: 400px 0; }
              }
              .skel {
                background: linear-gradient(90deg, #1e2333 25%, #252a3d 50%, #1e2333 75%);
                background-size: 800px 100%;
                animation: shimmer 1.4s infinite linear;
                border-radius: 6px;
              }
            `}</style>
            {/* Header skeleton */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <div className="skel" style={{ height: 12, width: 80 }} />
              <div className="skel" style={{ height: 24, width: 24, borderRadius: '50%' }} />
            </div>
            <div className="skel" style={{ height: 28, width: '60%', marginBottom: 10 }} />
            <div className="skel" style={{ height: 22, width: 100, borderRadius: 10, marginBottom: 20 }} />
            {/* Thesis skeleton */}
            <div className="skel" style={{ height: 80, width: '100%', marginBottom: 20 }} />
            {/* Agent panel skeletons */}
            {[1,2,3].map(i => (
              <div key={i} style={{ background: '#1a1d27', borderRadius: 8, padding: 16, marginBottom: 12 }}>
                <div className="skel" style={{ height: 11, width: 120, marginBottom: 12 }} />
                {[1,2,3].map(j => (
                  <div key={j} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div className="skel" style={{ height: 12, width: '45%' }} />
                    <div className="skel" style={{ height: 12, width: '25%' }} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : companyDetail ? (
          <CompanyDetailPanel data={companyDetail} onClose={closePanel} isMobile={isMobile} />
        ) : (
          <div className="detail-panel" style={{
            position: 'fixed', top: 0, right: 0, bottom: 0, width: isMobile ? '100%' : '500px',
            background: '#141720', borderLeft: '1px solid #2d3148', zIndex: 100,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
          }}>
            <div style={{ color: '#f87171', fontSize: '14px' }}>Failed to load company data.</div>
            <button
              onClick={closePanel}
              style={{
                padding: '6px 14px', background: '#1e293b', border: '1px solid #334155',
                borderRadius: '6px', color: '#94a3b8', cursor: 'pointer', fontSize: '13px',
              }}
            >Close</button>
          </div>
        )
      )}
    </div>
  )
}
