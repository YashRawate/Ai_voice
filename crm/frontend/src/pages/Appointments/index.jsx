import { useEffect, useMemo, useState } from 'react'
import DashboardLayout from '../../components/DashboardLayout'
import * as crm from '../../lib/crmApi'
import { CalendarCheck, MapPin, Phone, CheckCircle, XCircle, Clock } from 'lucide-react'
import { SAGE, SAGE_DARK, AMBER, AMBER_DARK, INK, INK_BODY, INK_MUTED } from '../../theme'

const STATUS_STYLE = {
  booked:    { bg: '#EAF0FF', ink: '#3355BB' },
  reminded:  { bg: '#E8F7F4', ink: '#0E7C6B' },
  visited:   { bg: '#EAF3E6', ink: SAGE_DARK },
  no_show:   { bg: '#FDECEC', ink: '#B23B3B' },
  cancelled: { bg: '#F1F1F1', ink: '#7A7A7A' },
}
const MODE_LABEL = { campus_visit: 'Campus visit', virtual_tour: 'Virtual tour', counselling: 'Counselling' }

// Start/end of a day (local) as ISO — n = day offset from today (0 today, -1 yesterday, +1 tomorrow)
function dayRange(offset) {
  const start = new Date(); start.setHours(0, 0, 0, 0); start.setDate(start.getDate() + offset)
  const end = new Date(start); end.setHours(23, 59, 59, 999)
  return { from: start.toISOString(), to: end.toISOString() }
}
function Badge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.cancelled
  return <span style={{ fontSize: 11, fontWeight: 600, color: s.ink, background: s.bg, padding: '3px 9px', borderRadius: 999, textTransform: 'capitalize' }}>{String(status).replace(/_/g, ' ')}</span>
}

const RANGES = [
  { key: 'yesterday', label: 'Yesterday', get: () => dayRange(-1) },
  { key: 'today',     label: 'Today',     get: () => dayRange(0) },
  { key: 'tomorrow',  label: 'Tomorrow',  get: () => dayRange(1) },
  { key: 'all',       label: 'All',       get: () => ({}) },
]

export default function Appointments() {
  const { user } = { user: JSON.parse(localStorage.getItem('user') || '{}') }
  const [range, setRange] = useState('today')
  const [customDate, setCustomDate] = useState('')   // yyyy-mm-dd — "any date"
  const [status, setStatus] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const notify = (t) => { setToast(t); setTimeout(() => setToast(null), 3000) }

  async function load() {
    setLoading(true)
    try {
      let params = {}
      if (customDate) {
        const start = new Date(customDate + 'T00:00:00'); const end = new Date(customDate + 'T23:59:59.999')
        params = { from: start.toISOString(), to: end.toISOString() }
      } else {
        params = RANGES.find(r => r.key === range)?.get() || {}
      }
      if (status) params.status = status
      const data = await crm.listAppointments(params)
      setItems(Array.isArray(data) ? data : [])
    } catch (e) { notify(e.response?.data?.message || 'Failed to load appointments') }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [range, customDate, status])

  async function mark(id, s) {
    try { await crm.setAppointmentStatus(id, s); notify(`Marked ${s.replace('_', ' ')}`); load() }
    catch (e) { notify(e.response?.data?.message || 'Could not update') }
  }

  const counts = useMemo(() => items.reduce((a, x) => ((a[x.status] = (a[x.status] || 0) + 1), a), {}), [items])

  const pill = (active) => ({
    padding: '7px 14px', borderRadius: 9, border: `1px solid ${active ? SAGE : '#E3E3E3'}`,
    background: active ? SAGE : '#fff', color: active ? '#fff' : INK_BODY, fontSize: 13,
    fontWeight: 600, cursor: 'pointer',
  })

  return (
    <DashboardLayout>
      <div style={{ padding: '4px 4px 40px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <CalendarCheck size={22} color={SAGE_DARK} />
          <h1 style={{ fontSize: 24, fontWeight: 700, color: INK, margin: 0 }}>Appointments</h1>
        </div>
        <p style={{ color: INK_MUTED, fontSize: 13, margin: '0 0 18px' }}>
          Campus visits & counselling sessions · {items.length} in view
          {counts.visited ? ` · ${counts.visited} visited` : ''}{counts.no_show ? ` · ${counts.no_show} no-show` : ''}
        </p>

        {/* Date range filters */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 18 }}>
          {RANGES.map(r => (
            <button key={r.key} style={pill(!customDate && range === r.key)}
              onClick={() => { setCustomDate(''); setRange(r.key) }}>{r.label}</button>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 4 }}>
            <span style={{ fontSize: 13, color: INK_MUTED }}>Any date:</span>
            <input type="date" value={customDate} onChange={e => setCustomDate(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 9, border: `1px solid ${customDate ? SAGE : '#E3E3E3'}`, fontSize: 13 }} />
            {customDate && <button style={{ ...pill(false), padding: '6px 10px' }} onClick={() => setCustomDate('')}>Clear</button>}
          </div>
          <select value={status} onChange={e => setStatus(e.target.value)}
            style={{ padding: '7px 12px', borderRadius: 9, border: '1px solid #E3E3E3', fontSize: 13, marginLeft: 'auto' }}>
            <option value="">All statuses</option>
            {['booked', 'reminded', 'visited', 'no_show', 'cancelled'].map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
        </div>

        <div style={{ background: '#fff', border: '1px solid #EEE', borderRadius: 14, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#FAFAF8', color: INK_MUTED, textAlign: 'left' }}>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>When</th>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>Student</th>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>Branch</th>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>Mode</th>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '11px 14px', fontWeight: 600 }}>Mark</th>
              </tr>
            </thead>
            <tbody>
              {items.map(a => (
                <tr key={a._id} style={{ borderTop: '1px solid #F1F1F1' }}>
                  <td style={{ padding: '11px 14px', whiteSpace: 'nowrap' }}>
                    <div style={{ fontWeight: 600, color: INK }}>{new Date(a.scheduledFor).toLocaleDateString()}</div>
                    <div style={{ color: INK_MUTED, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={11} />{new Date(a.scheduledFor).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </td>
                  <td style={{ padding: '11px 14px' }}>
                    <div style={{ fontWeight: 600, color: INK }}>{a.studentName || a.leadId?.name || '—'}</div>
                    {a.studentPhone && <div style={{ color: INK_MUTED, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}><Phone size={11} />{a.studentPhone}</div>}
                  </td>
                  <td style={{ padding: '11px 14px', color: INK_BODY }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><MapPin size={12} color={INK_MUTED} />{a.branchId?.name || '—'}</span>
                  </td>
                  <td style={{ padding: '11px 14px', color: INK_BODY }}>{MODE_LABEL[a.mode] || a.mode}</td>
                  <td style={{ padding: '11px 14px' }}><Badge status={a.status} /></td>
                  <td style={{ padding: '11px 14px' }}>
                    {['visited', 'cancelled', 'no_show'].includes(a.status) ? <span style={{ color: '#C7C7C7' }}>—</span> : (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button title="Visited" onClick={() => mark(a._id, 'visited')}
                          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 9px', borderRadius: 8, border: 'none', background: '#EAF3E6', color: SAGE_DARK, fontWeight: 600, fontSize: 12, cursor: 'pointer' }}>
                          <CheckCircle size={13} /> Visited
                        </button>
                        <button title="No-show" onClick={() => mark(a._id, 'no_show')}
                          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 9px', borderRadius: 8, border: 'none', background: '#FDECEC', color: '#B23B3B', fontWeight: 600, fontSize: 12, cursor: 'pointer' }}>
                          <XCircle size={13} /> No-show
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && items.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: INK_MUTED }}>No appointments in this range.</div>
          )}
          {loading && <div style={{ padding: 40, textAlign: 'center', color: INK_MUTED }}>Loading…</div>}
        </div>
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, background: INK, color: '#fff', padding: '10px 16px', borderRadius: 10, fontSize: 13, zIndex: 100 }}>{toast}</div>
      )}
    </DashboardLayout>
  )
}
