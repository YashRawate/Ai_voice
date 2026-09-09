import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import { Zap, RefreshCw, Share2, Plus, CheckCircle } from 'lucide-react'

export default function IntegrationsHub() {
  const [loading, setLoading] = useState(false)
  const [workflows, setWorkflows] = useState([])
  const [payments, setPayments] = useState([])
  const [lmsConfig, setLmsConfig] = useState(null)
  const [message, setMessage] = useState('')
  const [paymentModal, setPaymentModal] = useState(false)
  const [newPayment, setNewPayment] = useState({ registrationNumber: '', studentName: '', feeType: 'Application Fee', amount: 1000 })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [wRes, pRes, lRes] = await Promise.all([
        axios.get('/api/unified-crm/workflows', { withCredentials: true }),
        axios.get('/api/unified-crm/payments', { withCredentials: true }),
        axios.get('/api/unified-crm/lms', { withCredentials: true })
      ])
      if (wRes.data.success) setWorkflows(wRes.data.rules)
      if (pRes.data.success) setPayments(pRes.data.payments)
      if (lRes.data.success) setLmsConfig(lRes.data.config)
    } catch (err) {
      console.error('Error fetching integrations data', err)
    }
  }

  const handleLmsSync = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/lms/sync', {}, { withCredentials: true })
      setMessage(res.data.message)
      fetchData()
    } catch (err) {
      setMessage('LMS sync failed')
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerRemarketing = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/remarketing/sync', { platform: 'all' }, { withCredentials: true })
      setMessage(res.data.message)
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
      fetchData()
    } catch (err) {
      setMessage('Payment link error')
    } finally {
      setLoading(false)
    }
  }

  const handleIssueOffer = async (paymentId) => {
    try {
      const res = await axios.post('/api/unified-crm/payments/issue-offer', { paymentId }, { withCredentials: true })
      setMessage(res.data.message)
      fetchData()
    } catch (err) {
      setMessage('Offer issue error')
    }
  }

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 1100, margin: '0 auto', fontFamily: 'sans-serif', color: '#2C2C2C' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#1F2937' }}>Automation & Integrations Hub</h1>
            <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>Workflows, remarketing sync, fee payment links, digital offer letters, and LMS handoffs.</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={() => setPaymentModal(true)} style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '8px 14px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              + Payment Link
            </button>
            <button onClick={handleLmsSync} disabled={loading} style={{ background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', padding: '8px 14px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              Sync LMS
            </button>
            <button onClick={handleTriggerRemarketing} disabled={loading} style={{ background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', padding: '8px 14px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              Sync Audiences
            </button>
          </div>
        </div>

        {message && (
          <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E40AF', padding: '10px 14px', borderRadius: 8, marginBottom: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle size={16} /> {message}
            </div>
            <button onClick={() => setMessage('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1E40AF', fontWeight: 700 }}>✕</button>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Workflow Rules</h4>
            {workflows.map(w => (
              <div key={w._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13 }}>
                <div style={{ fontWeight: 600 }}>{w.name}</div>
                <div style={{ fontSize: 12, color: '#6B7280' }}>Trigger: {w.triggerEvent}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Payments & Offer Letters</h4>
            {payments.map(p => (
              <div key={p._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{p.studentName}</div>
                  <div style={{ fontSize: 12, color: '#6B7280' }}>{p.feeType} - ₹{p.amount}</div>
                </div>
                {p.offerLetterIssued ? (
                  <span style={{ color: '#059669', fontSize: 11, fontWeight: 600 }}>Issued PDF ✓</span>
                ) : (
                  <button onClick={() => handleIssueOffer(p._id)} style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '3px 8px', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>Issue Offer</button>
                )}
              </div>
            ))}
          </div>
        </div>

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
