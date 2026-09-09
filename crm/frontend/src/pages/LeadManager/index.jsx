import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import { Users, RefreshCw, CheckCircle, ShieldCheck } from 'lucide-react'

export default function LeadManager() {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [counselors, setCounselors] = useState([])
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [oRes, fRes] = await Promise.all([
        axios.get('/api/unified-crm/overview', { withCredentials: true }),
        axios.get('/api/unified-crm/analytics/funnel', { withCredentials: true })
      ])
      if (oRes.data.success) setStats(oRes.data.stats)
      if (fRes.data.success) setCounselors(fRes.data.counselorPerformance)
    } catch (err) {
      console.error('Error fetching lead data', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAutoAssign = async () => {
    try {
      setLoading(true)
      const res = await axios.post('/api/unified-crm/lead-allocation/auto-assign', {}, { withCredentials: true })
      setMessage(res.data.message)
      fetchData()
    } catch (err) {
      setMessage('Failed to execute allocation: ' + (err.response?.data?.message || err.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 1100, margin: '0 auto', fontFamily: 'sans-serif', color: '#2C2C2C' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#1F2937' }}>Lead Management & Allocation</h1>
            <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>Centralizes inquiries and round-robin counselor distribution.</p>
          </div>
          {stats && (
            <div style={{ background: '#F3F4F6', padding: '6px 14px', borderRadius: 8, fontSize: 13 }}>
              Total Inquiries: <strong>{stats.totalLeads}</strong>
            </div>
          )}
        </div>

        {message && (
          <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E40AF', padding: '10px 14px', borderRadius: 8, marginBottom: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle size={16} /> {message}
            </div>
            <button onClick={() => setMessage('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1E40AF', fontWeight: 700 }}>✕</button>
          </div>
        )}

        <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E5E7EB', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Round-Robin Lead Allocator</h3>
              <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>Distributes unassigned student inquiries across active counselors.</p>
            </div>
            <button
              onClick={handleAutoAssign}
              disabled={loading}
              style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '10px 18px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <RefreshCw size={15} /> Execute Allocation
            </button>
          </div>
        </div>

        <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E5E7EB' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 14 }}>Active Counselors & Quota</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB', textAlign: 'left' }}>
                <th style={{ padding: 10 }}>Counselor Name</th>
                <th style={{ padding: 10 }}>Assigned Leads</th>
                <th style={{ padding: 10 }}>Verified</th>
                <th style={{ padding: 10 }}>Conversion Rate</th>
              </tr>
            </thead>
            <tbody>
              {counselors.map((c, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                  <td style={{ padding: 10, fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: 10 }}>{c.assigned}</td>
                  <td style={{ padding: 10 }}>{c.verified}</td>
                  <td style={{ padding: 10 }}><span style={{ background: '#DCFCE7', color: '#166534', padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>{c.conversionRate}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  )
}
