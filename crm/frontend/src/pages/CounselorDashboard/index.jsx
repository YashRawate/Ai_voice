import { useState, useEffect } from 'react'
import DashboardLayout from '../../components/DashboardLayout'
import * as crm from '../../lib/crmApi'
import { INK, INK_BODY, INK_MUTED, SAGE } from '../../theme'
import { UserCheck, Clock, CheckCircle, XCircle, FileText, Send } from 'lucide-react'

export default function CounselorDashboard() {
  const [counselorId, setCounselorId] = useState('AEC001')
  const [counselorsList, setCounselorsList] = useState([])
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [remarkInput, setRemarkInput] = useState('')

  async function loadCounselorData() {
    setLoading(true)
    try {
      const [cRes, sRes] = await Promise.all([
        crm.listCounselors(),
        crm.listStudentRegistrations({ counselorId })
      ])
      if (cRes.counselors) setCounselorsList(cRes.counselors)
      if (sRes.students) setStudents(sRes.students)
    } catch (err) {
      console.error('Failed to load counselor data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCounselorData()
  }, [counselorId])

  const todayStr = new Date().toISOString().split('T')[0]
  const todayCount = students.filter(s => s.registrationDate === todayStr).length
  const pendingCount = students.filter(s => s.admissionStatus === 'Pending').length
  const approvedCount = students.filter(s => s.admissionStatus === 'Approved').length
  const rejectedCount = students.filter(s => s.admissionStatus === 'Rejected').length

  return (
    <DashboardLayout activeItem="Counselor Portal">
      <div style={{ padding: '0 0 40px', fontFamily: 'Inter, sans-serif' }}>
        
        {/* Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: INK }}>Admission Counselor Portal</h1>
            <p style={{ color: INK_MUTED, fontSize: 13, margin: '4px 0 0', fontWeight: 500 }}>Students Assigned & Registered Under Your Counselor ID</p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#FFF', padding: '8px 16px', borderRadius: 12, border: '1px solid #E8E8E8', boxShadow: '0 2px 6px rgba(0,0,0,0.02)' }}>
            <span style={{ fontSize: 12, color: INK_MUTED, fontWeight: 700 }}>Select Counselor ID:</span>
            <select
              value={counselorId}
              onChange={e => setCounselorId(e.target.value)}
              style={{ background: '#FAFAFA', border: '1px solid #2563EB', color: '#2563EB', fontWeight: 800, padding: '6px 12px', borderRadius: 8, outline: 'none', cursor: 'pointer' }}
            >
              {counselorsList.map(c => (
                <option key={c._id} value={c.counselorId}>{c.counselorId} - {c.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Metric Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 16, marginBottom: 24 }}>
          <StatCard icon={UserCheck} title="My Total Registrations" value={students.length} color="#2563EB" />
          <StatCard icon={Clock} title="Today's Registrations" value={todayCount} color="#818CF8" />
          <StatCard icon={FileText} title="Pending Review" value={pendingCount} color="#D97706" />
          <StatCard icon={CheckCircle} title="Approved Admissions" value={approvedCount} color="#16A34A" />
          <StatCard icon={XCircle} title="Rejected Students" value={rejectedCount} color="#DC2626" />
        </div>

        {/* Student Table */}
        <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, overflow: 'hidden', boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
          <div style={{ padding: '18px 20px', borderBottom: '1px solid #E8E8E8', fontWeight: 800, fontSize: 15, color: '#2563EB', display: 'flex', alignItems: 'center', gap: 8 }}>
            <UserCheck size={18} /> Assigned Student Registrations ({counselorId})
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#F8FAFC', color: INK_MUTED, borderBottom: '1px solid #E8E8E8' }}>
                <th style={thStyle}>Reg Number</th>
                <th style={thStyle}>Student Name</th>
                <th style={thStyle}>Mobile & Email</th>
                <th style={thStyle}>Course Interested</th>
                <th style={thStyle}>SSC / Inter %</th>
                <th style={thStyle}>Reg Date</th>
                <th style={thStyle}>Verification</th>
                <th style={thStyle}>Admission Status</th>
                <th style={thStyle}>Action</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 36, color: INK_MUTED, fontWeight: 500 }}>No student registrations linked to counselor {counselorId} yet.</td>
                </tr>
              ) : (
                students.map(s => (
                  <tr key={s._id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={tdStyle}><strong style={{ color: '#2563EB', fontWeight: 800 }}>{s.registrationNumber}</strong></td>
                    <td style={tdStyle}><span style={{ fontWeight: 700, color: INK }}>{s.name}</span></td>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600, color: INK }}>{s.mobile}</div>
                      <div style={{ fontSize: 11, color: INK_MUTED }}>{s.email}</div>
                    </td>
                    <td style={tdStyle}>{s.courseInterested}</td>
                    <td style={tdStyle}>{s.sscPercentage}% / {s.interPercentage}%</td>
                    <td style={tdStyle}>{s.registrationDate}</td>
                    <td style={tdStyle}>
                      <span style={{ fontSize: 11, fontWeight: 800, padding: '3px 8px', borderRadius: 6, background: '#FAFAFA', color: s.verificationStatus === 'Verified' ? '#15803D' : '#B45309', border: '1px solid #E2E8F0' }}>
                        {s.verificationStatus}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: s.admissionStatus === 'Approved' ? '#15803D' : s.admissionStatus === 'Rejected' ? '#DC2626' : '#B45309' }}>
                        {s.admissionStatus}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <button onClick={() => setSelectedStudent(s)} style={{ background: '#2563EB', color: '#FFF', border: 'none', padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
                        View / Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Review Drawer Modal */}
        {selectedStudent && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99 }}>
            <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 20, width: '90%', maxWidth: 540, padding: 28, boxShadow: '0 20px 50px rgba(0,0,0,0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E8E8E8', paddingBottom: 14, marginBottom: 18 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#2563EB' }}>Review Student: {selectedStudent.name}</h3>
                <button onClick={() => setSelectedStudent(null)} style={{ background: 'none', border: 'none', color: INK_MUTED, fontSize: 20, cursor: 'pointer' }}>✕</button>
              </div>

              <div style={{ fontSize: 13, color: INK_BODY, marginBottom: 20, lineHeight: 1.6 }}>
                <p style={{ margin: '4px 0' }}><strong>Mobile:</strong> {selectedStudent.mobile} | <strong>Email:</strong> {selectedStudent.email}</p>
                <p style={{ margin: '4px 0' }}><strong>Address:</strong> {selectedStudent.address}, {selectedStudent.city}, {selectedStudent.state}</p>
                <p style={{ margin: '4px 0' }}><strong>Father Name:</strong> {selectedStudent.fatherName} | <strong>Mother Name:</strong> {selectedStudent.motherName}</p>
                <p style={{ margin: '4px 0' }}><strong>Course:</strong> {selectedStudent.courseInterested} ({selectedStudent.department})</p>
              </div>

              <div style={{ background: '#FAFAFA', border: '1px solid #E8E8E8', borderRadius: 12, padding: 16, marginBottom: 20 }}>
                <label style={{ fontSize: 12, color: INK_MUTED, fontWeight: 700, display: 'block', marginBottom: 8 }}>Add Counselor Remarks / Recommendation</label>
                <textarea
                  rows={3}
                  value={remarkInput}
                  onChange={e => setRemarkInput(e.target.value)}
                  placeholder="e.g. Verified 10th & Inter memos. Student is eligible for Merit Scholarship."
                  style={{ width: '100%', background: '#FFF', border: '1px solid #CBD5E1', borderRadius: 8, color: INK, padding: 10, fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button onClick={() => setSelectedStudent(null)} style={{ background: '#F1F5F9', color: INK_BODY, border: 'none', padding: '10px 18px', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
                  Close
                </button>
                <button onClick={() => { alert('Student recommendation forwarded to Admin'); setSelectedStudent(null) }} style={{ background: '#2563EB', color: '#FFF', border: 'none', padding: '10px 20px', borderRadius: 8, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Send size={14} /> Forward to Admin
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}

function StatCard({ icon: Icon, title, value, color }) {
  return (
    <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 18, boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: INK_MUTED, fontWeight: 700 }}>{title}</span>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={16} color={color} />
        </div>
      </div>
      <div style={{ fontSize: 26, fontWeight: 900, color: INK }}>{value}</div>
    </div>
  )
}

const thStyle = { padding: '14px 16px', fontWeight: 800, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }
const tdStyle = { padding: '14px 16px', color: INK_BODY, fontWeight: 500 }
