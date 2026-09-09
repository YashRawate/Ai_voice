import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import {
  Users, Share2, Layers, Cpu, TrendingUp, DollarSign,
  GraduationCap, ShieldCheck, HelpCircle, Upload, CheckCircle,
  RefreshCw, Send, Plus, Zap, Eye, EyeOff, MessageSquare, Play
} from 'lucide-react'

export default function UnifiedCrm() {
  const [activeTab, setActiveTab] = useState('leads')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [message, setMessage] = useState('')

  // Combined module states
  const [funnelData, setFunnelData] = useState([])
  const [counselors, setCounselors] = useState([])
  const [remarketingSyncs, setRemarketingSyncs] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [predictive, setPredictive] = useState(null)
  const [payments, setPayments] = useState([])
  const [lmsConfig, setLmsConfig] = useState(null)
  const [roles, setRoles] = useState([])
  const [tickets, setTickets] = useState([])

  // AI Chat & PII state
  const [chatMessages, setChatMessages] = useState([
    { sender: 'ai', text: 'Hello! I am your Enrolo Admissions Assistant. Ask me anything about lead allocations, payment links, remarketing, or LMS handoffs!' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [maskPii, setMaskPii] = useState(true)

  // Quick modals
  const [importModal, setImportModal] = useState(false)
  const [csvText, setCsvText] = useState('')
  const [paymentModal, setPaymentModal] = useState(false)
  const [newPayment, setNewPayment] = useState({ registrationNumber: '', studentName: '', feeType: 'Application Fee', amount: 1000 })
  const [workflowModal, setWorkflowModal] = useState(false)
  const [newWorkflow, setNewWorkflow] = useState({ name: '', triggerEvent: 'lead_created', actionType: 'send_whatsapp' })

  useEffect(() => {
    fetchOverview()
    fetchAllModuleData()
  }, [])

  const fetchOverview = async () => {
    try {
      const res = await axios.get('/api/unified-crm/overview', { withCredentials: true })
      if (res.data.success) setStats(res.data.stats)
    } catch (err) {
      console.error('Error fetching overview', err)
    }
  }

  const fetchAllModuleData = async () => {
    setLoading(true)
    try {
      const [fRes, rRes, wRes, pRes, payRes, lmsRes, rbacRes, tRes] = await Promise.all([
        axios.get('/api/unified-crm/analytics/funnel', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/remarketing', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/workflows', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/predictive/insights', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/payments', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/lms', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/security/rbac', { withCredentials: true }).catch(() => null),
        axios.get('/api/unified-crm/support/tickets', { withCredentials: true }).catch(() => null)
      ])

      if (fRes?.data?.success) {
        setFunnelData(fRes.data.funnel)
        setCounselors(fRes.data.counselorPerformance)
      }
      if (rRes?.data?.success) setRemarketingSyncs(rRes.data.syncs)
      if (wRes?.data?.success) setWorkflows(wRes.data.rules)
      if (pRes?.data?.success) setPredictive(pRes.data)
      if (payRes?.data?.success) setPayments(payRes.data.payments)
      if (lmsRes?.data?.success) setLmsConfig(lmsRes.data.config)
      if (rbacRes?.data?.success) setRoles(rbacRes.data.roles)
      if (tRes?.data?.success) setTickets(tRes.data.tickets)
    } catch (err) {
      console.error('Module data load error', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAutoAssign = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/lead-allocation/auto-assign', {}, { withCredentials: true })
      setMessage(res.data.message)
      fetchOverview()
    } catch (err) {
      setMessage('Failed: ' + (err.response?.data?.message || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleBulkImport = async () => {
    try {
      setLoading(true)
      let items = []
      if (csvText.trim()) {
        const lines = csvText.trim().split('\n')
        items = lines.map(l => {
          const parts = l.split(',')
          return { name: parts[0]?.trim() || 'Walk-In Applicant', phone: parts[1]?.trim() || '9876543210', interPercentage: Number(parts[2]) || 85, entranceExam: parts[3]?.trim() || 'EAMCET', walkIn: true }
        })
      } else {
        items = [
          { name: 'Rohan Sharma', phone: '+919876543210', interPercentage: 92, entranceExam: 'EAMCET', walkIn: true },
          { name: 'Sneha Patel', phone: '+919876543211', interPercentage: 88, entranceExam: 'JEE', walkIn: false }
        ]
      }
      const res = await axios.post('/api/unified-crm/bulk-import', { items }, { withCredentials: true })
      setMessage(res.data.message)
      setImportModal(false)
      setCsvText('')
      fetchOverview()
    } catch (err) {
      setMessage('Import error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerRemarketing = async (platform) => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/remarketing/sync', { platform }, { withCredentials: true })
      setMessage(res.data.message)
      fetchAllModuleData()
    } catch (err) {
      setMessage('Sync error')
    } finally {
      setLoading(false)
    }
  }

  const handleGeneratePayment = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/payments/generate-link', newPayment, { withCredentials: true })
      setMessage(res.data.message)
      setPaymentModal(false)
      fetchAllModuleData()
    } catch (err) {
      setMessage('Failed to generate payment link')
    } finally {
      setLoading(false)
    }
  }

  const handleIssueOffer = async (paymentId) => {
    try {
      const res = await axios.post('/api/unified-crm/payments/issue-offer', { paymentId }, { withCredentials: true })
      setMessage(res.data.message)
      fetchAllModuleData()
    } catch (err) {
      setMessage('Offer issuance failed')
    }
  }

  const handleLmsSync = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/lms/sync', {}, { withCredentials: true })
      setMessage(res.data.message)
      fetchAllModuleData()
    } catch (err) {
      setMessage('LMS sync failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSendAiChat = async () => {
    if (!chatInput.trim()) return
    const q = chatInput
    setChatMessages(p => [...p, { sender: 'user', text: q }])
    setChatInput('')
    try {
      const res = await axios.post('/api/unified-crm/support/chat-ai', { query: q }, { withCredentials: true })
      setChatMessages(p => [...p, { sender: 'ai', text: res.data.reply }])
    } catch (err) {
      setChatMessages(p => [...p, { sender: 'ai', text: 'Error connecting to support AI assistant.' }])
    }
  }

  const tabs = [
    { id: 'leads', label: '1. Lead & Application Hub', icon: Users },
    { id: 'analytics', label: '2. Analytics & Yield Forecast', icon: TrendingUp },
    { id: 'automations', label: '3. Automations & Integrations', icon: Zap },
    { id: 'security', label: '4. Control & AI Support', icon: ShieldCheck }
  ]

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 1240, margin: '0 auto', fontFamily: 'sans-serif', color: '#2C2C2C' }}>
        
        {/* Header Title */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#1F2937' }}>
              Unified CRM & Admissions Suite
            </h1>
            <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>
              Streamlined management of leads, AI applications, analytics, payment links, LMS, and support.
            </p>
          </div>
          {stats && (
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ background: '#F3F4F6', padding: '6px 12px', borderRadius: 8, fontSize: 12 }}>
                Inquiries: <strong>{stats.totalLeads}</strong>
              </div>
              <div style={{ background: '#ECFDF5', color: '#065F46', padding: '6px 12px', borderRadius: 8, fontSize: 12 }}>
                LMS Enrolled: <strong>{stats.lmsSyncCount}</strong>
              </div>
            </div>
          )}
        </div>

        {/* Message Alert */}
        {message && (
          <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E40AF', padding: '10px 14px', borderRadius: 8, marginBottom: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500 }}>
              <CheckCircle size={16} /> {message}
            </div>
            <button onClick={() => setMessage('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1E40AF', fontWeight: 700 }}>✕</button>
          </div>
        )}

        {/* Streamlined 4 Tabs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, borderBottom: '1px solid #E5E7EB', marginBottom: 20 }}>
          {tabs.map(t => {
            const Icon = t.icon
            const active = activeTab === t.id
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justify: 'center',
                  gap: 8,
                  padding: '12px 10px',
                  borderRadius: '8px 8px 0 0',
                  border: 'none',
                  borderBottom: active ? '3px solid #7D9B76' : '3px solid transparent',
                  background: active ? '#FFFFFF' : '#F9FAFB',
                  color: active ? '#7D9B76' : '#4B5563',
                  fontWeight: active ? 600 : 500,
                  fontSize: 13,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}>
                <Icon size={16} color={active ? '#7D9B76' : '#6B7280'} />
                {t.label}
              </button>
            )
          })}
        </div>

        {/* HUB 1: LEAD & APPLICATION HUB */}
        {activeTab === 'leads' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Quick Actions Bar */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button
                onClick={handleAutoAssign}
                disabled={loading}
                style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '10px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <RefreshCw size={15} /> Execute Round-Robin Lead Allocation
              </button>
              <button
                onClick={() => setImportModal(true)}
                style={{ background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', padding: '10px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Upload size={15} /> Bulk Import Applications / Walk-Ins
              </button>
            </div>

            {/* Hub Details Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
              <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px 0' }}>Multi-Channel Lead Allocation</h3>
                <p style={{ fontSize: 13, color: '#6B7280', margin: '0 0 12px 0' }}>Round-robin auto-assigns unallocated web inquiries, Priya AI calls, and QR walk-in registrations across counselors.</p>
                <div style={{ fontSize: 12, background: '#F3F4F6', padding: 8, borderRadius: 6, color: '#374151', fontWeight: 500 }}>
                  Active Counselors Ready: <strong>{counselors.length || 3} Counselors</strong>
                </div>
              </div>

              <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px 0' }}>AI Application Manager & Tagging</h3>
                <p style={{ fontSize: 13, color: '#6B7280', margin: '0 0 12px 0' }}>Auto-scores student academic intent and applies tags (High Academic, Exam Qualified, Walk-In).</p>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ background: '#DCFCE7', color: '#166534', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>High Academic (&gt;80%)</span>
                  <span style={{ background: '#E0E7FF', color: '#3730A3', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>Exam Qualified</span>
                  <span style={{ background: '#FEF3C7', color: '#92400E', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>Priority Walk-In</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* HUB 2: ANALYTICS & YIELD FORECAST */}
        {activeTab === 'analytics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Conversion Funnel */}
            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E5E7EB' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0' }}>Admissions Conversion Funnel</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {funnelData.map((f, idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                      <span>{f.stage}</span>
                      <span>{f.count} ({f.conversion}%)</span>
                    </div>
                    <div style={{ height: 8, background: '#E5E7EB', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.max(f.conversion, 4)}%`, height: '100%', background: '#7D9B76' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Predictive Forecast & Counselor SLA */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {predictive && (
                <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                  <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 10px 0' }}>Predictive Session Insights</h4>
                  <div style={{ fontSize: 13, color: '#4B5563' }}>Forecast Yield Rate: <strong style={{ color: '#7D9B76' }}>{predictive.predictions.forecastYield}%</strong></div>
                  <div style={{ fontSize: 13, color: '#4B5563', marginTop: 4 }}>Predicted Enrollments: <strong>{predictive.predictions.predictedEnrollments}</strong></div>
                  <div style={{ fontSize: 12, color: '#DC2626', marginTop: 8 }}>Drop-Out Risk: {predictive.predictions.dropOutRiskPercentage}%</div>
                </div>
              )}

              <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 10px 0' }}>Counselor Performance SLA</h4>
                <div style={{ fontSize: 13, color: '#4B5563' }}>Active Counselors: <strong>{counselors.length}</strong></div>
                <div style={{ fontSize: 13, color: '#4B5563', marginTop: 4 }}>Avg SLA Response: <strong>1.8 hours</strong></div>
                <div style={{ fontSize: 12, color: '#059669', marginTop: 8 }}>Avg Conversion: 80%</div>
              </div>
            </div>
          </div>
        )}

        {/* HUB 3: AUTOMATIONS & INTEGRATIONS */}
        {activeTab === 'automations' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button
                onClick={() => setPaymentModal(true)}
                style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '10px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Plus size={15} /> Generate Payment Link
              </button>
              <button
                onClick={handleLmsSync}
                disabled={loading}
                style={{ background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', padding: '10px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <RefreshCw size={15} /> Sync Enrolled Roster to LMS
              </button>
              <button
                onClick={() => handleTriggerRemarketing('all')}
                disabled={loading}
                style={{ background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', padding: '10px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Share2 size={15} /> Sync Remarketing Audiences
              </button>
            </div>

            {/* Workflow & Payments List */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Active Workflow Automations</h4>
                {workflows.slice(0, 2).map(w => (
                  <div key={w._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13 }}>
                    <div style={{ fontWeight: 600 }}>{w.name}</div>
                    <div style={{ fontSize: 12, color: '#6B7280' }}>Trigger: {w.triggerEvent}</div>
                  </div>
                ))}
              </div>

              <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Payments & Offer Letters</h4>
                {payments.slice(0, 2).map(p => (
                  <div key={p._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{p.studentName}</div>
                      <div style={{ fontSize: 12, color: '#6B7280' }}>{p.feeType} - ₹{p.amount}</div>
                    </div>
                    {p.offerLetterIssued ? (
                      <span style={{ color: '#059669', fontSize: 11, fontWeight: 600 }}>Offer Issued ✓</span>
                    ) : (
                      <button onClick={() => handleIssueOffer(p._id)} style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '3px 8px', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>Issue Offer</button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* HUB 4: CONTROL & AI SUPPORT */}
        {activeTab === 'security' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
            {/* Left: Security & HelpDesk Tickets */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h4 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Security & Data Protection (PII)</h4>
                  <p style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>Role-based controls & personal data masking.</p>
                </div>
                <button
                  onClick={() => setMaskPii(!maskPii)}
                  style={{ background: maskPii ? '#F3F4F6' : '#FEF3C7', border: '1px solid #D1D5DB', padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {maskPii ? <EyeOff size={14} /> : <Eye size={14} />}
                  {maskPii ? 'PII Masked' : 'PII Unmasked'}
                </button>
              </div>

              <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
                <h4 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>Institution HelpDesk Tickets</h4>
                {tickets.map(t => (
                  <div key={t._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13 }}>
                    <div style={{ fontWeight: 600 }}>{t.subject}</div>
                    <div style={{ fontSize: 12, color: '#6B7280' }}>Status: <strong style={{ color: t.status === 'Open' ? '#D97706' : '#059669' }}>{t.status}</strong></div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: 24/7 AI Live Chat Widget */}
            <div style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 12, display: 'flex', flexDirection: 'column', height: 420 }}>
              <div style={{ background: '#7D9B76', color: 'white', padding: '10px 14px', borderRadius: '12px 12px 0 0', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <MessageSquare size={15} /> 24/7 AI Support Assistant
              </div>
              <div style={{ flex: 1, padding: 12, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {chatMessages.map((m, i) => (
                  <div key={i} style={{ alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', background: m.sender === 'user' ? '#7D9B76' : '#F3F4F6', color: m.sender === 'user' ? 'white' : '#1F2937', padding: '7px 10px', borderRadius: 8, maxWidth: '85%', fontSize: 12 }}>
                    {m.text}
                  </div>
                ))}
              </div>
              <div style={{ padding: 8, borderTop: '1px solid #E5E7EB', display: 'flex', gap: 6 }}>
                <input
                  type="text"
                  placeholder="Ask AI Assistant..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendAiChat()}
                  style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '6px 8px', fontSize: 12, outline: 'none' }}
                />
                <button onClick={handleSendAiChat} style={{ background: '#7D9B76', color: 'white', border: 'none', borderRadius: 6, padding: '0 10px', cursor: 'pointer' }}>
                  <Send size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: Bulk CSV Import */}
        {importModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: 'white', padding: 20, borderRadius: 12, width: 440, maxWidth: '90%' }}>
              <h3 style={{ marginTop: 0, fontSize: 16 }}>Bulk Import Applicants</h3>
              <textarea
                rows={4}
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder="Rohan Verma, 9876543210, 88, EAMCET"
                style={{ width: '100%', borderRadius: 6, border: '1px solid #D1D5DB', padding: 8, fontSize: 12, boxSizing: 'border-box' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
                <button onClick={() => setImportModal(false)} style={{ background: '#F3F4F6', border: 'none', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Cancel</button>
                <button onClick={handleBulkImport} style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '6px 14px', borderRadius: 6, fontWeight: 600, cursor: 'pointer', fontSize: 12 }}>Run Import</button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: Payment Link */}
        {paymentModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: 'white', padding: 20, borderRadius: 12, width: 400, maxWidth: '90%' }}>
              <h3 style={{ marginTop: 0, fontSize: 16 }}>Generate Payment Link</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input type="text" placeholder="Reg Number (e.g. AEC2026-000105)" value={newPayment.registrationNumber} onChange={(e) => setNewPayment({ ...newPayment, registrationNumber: e.target.value })} style={{ border: '1px solid #D1D5DB', padding: 8, borderRadius: 6, fontSize: 12 }} />
                <input type="text" placeholder="Student Name" value={newPayment.studentName} onChange={(e) => setNewPayment({ ...newPayment, studentName: e.target.value })} style={{ border: '1px solid #D1D5DB', padding: 8, borderRadius: 6, fontSize: 12 }} />
                <input type="number" placeholder="Amount (₹)" value={newPayment.amount} onChange={(e) => setNewPayment({ ...newPayment, amount: e.target.value })} style={{ border: '1px solid #D1D5DB', padding: 8, borderRadius: 6, fontSize: 12 }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
                <button onClick={() => setPaymentModal(false)} style={{ background: '#F3F4F6', border: 'none', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Cancel</button>
                <button onClick={handleGeneratePayment} style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '6px 14px', borderRadius: 6, fontWeight: 600, cursor: 'pointer', fontSize: 12 }}>Generate Link</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
