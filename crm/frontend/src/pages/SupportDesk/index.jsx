import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import { ShieldCheck, Eye, EyeOff, MessageSquare, Send } from 'lucide-react'

export default function SupportDesk() {
  const [maskPii, setMaskPii] = useState(true)
  const [tickets, setTickets] = useState([])
  const [chatMessages, setChatMessages] = useState([
    { sender: 'ai', text: 'Hello! I am your 24/7 Enrolo Assistant. How can I assist your admissions team today?' }
  ])
  const [chatInput, setChatInput] = useState('')

  useEffect(() => {
    fetchTickets()
  }, [])

  const fetchTickets = async () => {
    try {
      const res = await axios.get('/api/unified-crm/support/tickets', { withCredentials: true })
      if (res.data.success) setTickets(res.data.tickets)
    } catch (err) {
      console.error('Error fetching tickets', err)
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
      setChatMessages(p => [...p, { sender: 'ai', text: 'Error connecting to support assistant AI.' }])
    }
  }

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 1100, margin: '0 auto', fontFamily: 'sans-serif', color: '#2C2C2C' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#1F2937' }}>Security & Support Desk</h1>
            <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>RBAC security matrix, PII data protection, and 24/7 AI chat support.</p>
          </div>
          <button
            onClick={() => setMaskPii(!maskPii)}
            style={{ background: maskPii ? '#F3F4F6' : '#FEF3C7', border: '1px solid #D1D5DB', padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            {maskPii ? <EyeOff size={14} /> : <Eye size={14} />}
            {maskPii ? 'PII Masking Active' : 'PII Unmasked'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
          <div style={{ background: '#FFFFFF', padding: 18, borderRadius: 12, border: '1px solid #E5E7EB' }}>
            <h4 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px 0' }}>HelpDesk Tickets</h4>
            {tickets.map(t => (
              <div key={t._id} style={{ borderBottom: '1px solid #F3F4F6', padding: '8px 0', fontSize: 13 }}>
                <div style={{ fontWeight: 600 }}>{t.subject}</div>
                <div style={{ fontSize: 12, color: '#6B7280' }}>Submitted by: {t.submittedBy} | Status: <strong style={{ color: t.status === 'Open' ? '#D97706' : '#059669' }}>{t.status}</strong></div>
              </div>
            ))}
          </div>

          <div style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 12, display: 'flex', flexDirection: 'column', height: 420 }}>
            <div style={{ background: '#7D9B76', color: 'white', padding: '10px 14px', borderRadius: '12px 12px 0 0', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <MessageSquare size={15} /> 24/7 AI Live Chat Assistant
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
      </div>
    </DashboardLayout>
  )
}
