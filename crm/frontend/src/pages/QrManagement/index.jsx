import { useState, useEffect } from 'react'
import DashboardLayout from '../../components/DashboardLayout'
import * as crm from '../../lib/crmApi'
import { INK, INK_BODY, INK_MUTED, SAGE } from '../../theme'
import { QrCode, Plus, ExternalLink, Printer, Download, Building2, CheckCircle2, Sparkles } from 'lucide-react'

export default function QrManagement() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [printCampaign, setPrintCampaign] = useState(null)

  const [form, setForm] = useState({
    title: '', code: '', collegeName: 'Aditya University', department: 'Engineering & Technology', campus: 'Main Campus Surampalem', campaignName: 'Admissions 2026'
  })

  async function loadCampaigns() {
    setLoading(true)
    try {
      const res = await crm.listQrCampaigns()
      if (res.campaigns) setCampaigns(res.campaigns)
    } catch (err) {
      console.error('Failed to load QR campaigns:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCampaigns()
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    try {
      await crm.createQrCampaign(form)
      setShowModal(false)
      setForm({ title: '', code: '', collegeName: 'Aditya University', department: 'Engineering & Technology', campus: 'Main Campus Surampalem', campaignName: 'Admissions 2026' })
      loadCampaigns()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to create QR code campaign')
    }
  }

  function handlePrintPoster(campaign) {
    setPrintCampaign(campaign)
    setTimeout(() => {
      window.print()
    }, 300)
  }

  return (
    <DashboardLayout activeItem="QR Code Generator">
      <div style={{ padding: '0 0 40px', fontFamily: 'Inter, sans-serif' }}>
        
        {/* Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: INK }}>QR Code & Campaign Management</h1>
            <p style={{ color: INK_MUTED, fontSize: 13, margin: '4px 0 0', fontWeight: 500 }}>Generate Scannable QR Codes for Campus Posters & Print Physical Admission Flyers</p>
          </div>

          <button
            onClick={() => setShowModal(true)}
            style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#2563EB', color: '#FFF', padding: '10px 20px', borderRadius: 10, fontWeight: 800, border: 'none', cursor: 'pointer', boxShadow: '0 4px 12px rgba(37,99,235,0.25)' }}
          >
            <Plus size={16} /> Generate New QR Code
          </button>
        </div>

        {/* Printable Poster Section (Visible only when printing) */}
        {printCampaign && (
          <div id="printable-poster" style={{ display: 'none' }}>
            <style>{`
              @media print {
                body * { visibility: hidden; }
                #printable-poster, #printable-poster * { visibility: visible; }
                #printable-poster {
                  position: absolute;
                  left: 0; top: 0; width: 100%;
                  display: block !important;
                  background: #FFF;
                  padding: 40px 20px;
                  text-align: center;
                  font-family: Inter, sans-serif;
                }
              }
            `}</style>
            
            <div style={{ border: '8px solid #2563EB', borderRadius: 24, padding: 40, maxWidth: 650, margin: '0 auto', background: '#FFF' }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#1E40AF', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>
                ADITYA EDUCATIONAL INSTITUTIONS
              </div>
              <h1 style={{ fontSize: 32, fontWeight: 900, color: '#0F172A', margin: '0 0 10px' }}>
                ONLINE ADMISSION REGISTRATION 2026
              </h1>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#2563EB', marginBottom: 24 }}>
                {printCampaign.title} ({printCampaign.department})
              </div>

              {/* Scannable QR Code Image */}
              <div style={{ background: '#F8FAFC', border: '2px solid #CBD5E1', borderRadius: 20, padding: 24, display: 'inline-block', marginBottom: 24 }}>
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(printCampaign.targetUrl)}`}
                  alt={`QR Code for ${printCampaign.title}`}
                  style={{ width: 280, height: 280, display: 'block' }}
                />
                <div style={{ fontSize: 14, fontWeight: 800, color: '#0F172A', marginTop: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  CODE: {printCampaign.code}
                </div>
              </div>

              <div style={{ fontSize: 18, fontWeight: 800, color: '#0F172A', marginBottom: 8 }}>
                SCAN THIS QR CODE WITH YOUR PHONE CAMERA
              </div>
              <p style={{ fontSize: 14, color: '#475569', margin: 0 }}>
                Directly opens the verified online student admission application portal for {printCampaign.campus}.
              </p>
            </div>
          </div>
        )}

        {/* QR Campaign Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
          {campaigns.length === 0 ? (
            <div style={{ colSpan: 'all', background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 36, textAlign: 'center', color: INK_MUTED, fontWeight: 500 }}>
              No QR Code campaigns created yet. Click "Generate New QR Code" to get started.
            </div>
          ) : (
            campaigns.map(c => {
              const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(c.targetUrl)}`
              return (
                <div key={c._id} style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 20, padding: 24, boxShadow: '0 4px 16px rgba(0,0,0,0.02)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    {/* Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                      <div>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#2563EB', background: '#EFF6FF', padding: '3px 8px', borderRadius: 6, textTransform: 'uppercase' }}>
                          {c.code}
                        </span>
                        <h3 style={{ fontSize: 18, fontWeight: 800, margin: '8px 0 4px', color: INK }}>{c.title}</h3>
                        <div style={{ fontSize: 12, color: INK_MUTED, fontWeight: 500 }}>{c.collegeName} — {c.department}</div>
                      </div>
                    </div>

                    {/* Scannable QR Image Visual */}
                    <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 16, padding: 16, textAlign: 'center', marginBottom: 16 }}>
                      <img
                        src={qrImageUrl}
                        alt={`QR Code ${c.code}`}
                        style={{ width: 180, height: 180, margin: '0 auto', display: 'block', borderRadius: 8 }}
                      />
                      <div style={{ fontSize: 11, color: INK_MUTED, fontWeight: 600, marginTop: 8 }}>
                        Scan with Phone Camera to Open Portal
                      </div>
                    </div>

                    {/* Scan Analytics */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, background: '#FAFAFA', border: '1px solid #E8E8E8', padding: 12, borderRadius: 12, marginBottom: 16, textAlign: 'center' }}>
                      <div>
                        <div style={{ fontSize: 11, color: INK_MUTED, fontWeight: 600 }}>Total Scans</div>
                        <div style={{ fontSize: 18, fontWeight: 900, color: INK }}>{c.scansCount}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: INK_MUTED, fontWeight: 600 }}>Registered</div>
                        <div style={{ fontSize: 18, fontWeight: 900, color: '#16A34A' }}>{c.successfulRegistrations}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: INK_MUTED, fontWeight: 600 }}>Conversion</div>
                        <div style={{ fontSize: 18, fontWeight: 900, color: '#D97706' }}>{c.conversionRate}</div>
                      </div>
                    </div>
                  </div>

                  {/* Actions: Print QR & Download */}
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      onClick={() => handlePrintPoster(c)}
                      style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, background: '#2563EB', color: '#FFF', border: 'none', padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 800, cursor: 'pointer', boxShadow: '0 4px 12px rgba(37,99,235,0.2)' }}
                    >
                      <Printer size={16} /> Print QR Poster
                    </button>

                    <a
                      href={qrImageUrl}
                      download={`QR_${c.code}.png`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, background: '#F1F5F9', color: INK_BODY, border: '1px solid #CBD5E1', padding: '10px 14px', borderRadius: 10, textDecoration: 'none', fontSize: 13, fontWeight: 700 }}
                      title="Download Image"
                    >
                      <Download size={16} />
                    </a>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Generate Modal */}
        {showModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99 }}>
            <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 20, width: '90%', maxWidth: 480, padding: 28, boxShadow: '0 20px 50px rgba(0,0,0,0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E8E8E8', paddingBottom: 14, marginBottom: 18 }}>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: '#2563EB' }}>Generate QR Code Campaign</h3>
                <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', color: INK_MUTED, fontSize: 20, cursor: 'pointer' }}>✕</button>
              </div>

              <form onSubmit={handleCreate} style={{ display: 'grid', gap: 14 }}>
                <div>
                  <label style={labelStyle}>Campaign Title *</label>
                  <input required type="text" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} style={inputStyle} placeholder="e.g. Engineering Open Day 2026 QR" />
                </div>
                <div>
                  <label style={labelStyle}>Unique Code *</label>
                  <input required type="text" value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} style={inputStyle} placeholder="e.g. QR-ENG-2026" />
                </div>
                <div>
                  <label style={labelStyle}>Department</label>
                  <input type="text" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Campus</label>
                  <input type="text" value={form.campus} onChange={e => setForm({ ...form, campus: e.target.value })} style={inputStyle} />
                </div>

                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 12 }}>
                  <button type="button" onClick={() => setShowModal(false)} style={{ background: '#F1F5F9', color: INK_BODY, border: 'none', padding: '10px 18px', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
                    Cancel
                  </button>
                  <button type="submit" style={{ background: '#2563EB', color: '#FFF', border: 'none', padding: '10px 20px', borderRadius: 8, fontWeight: 800, cursor: 'pointer' }}>
                    Create QR Code
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}

const labelStyle = { fontSize: 12, fontWeight: 700, color: INK_MUTED, display: 'block', marginBottom: 4 }
const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  background: '#FAFAFA',
  border: '1px solid #E8E8E8',
  color: INK,
  fontSize: 13,
  fontWeight: 600,
  outline: 'none',
  boxSizing: 'border-box'
}
