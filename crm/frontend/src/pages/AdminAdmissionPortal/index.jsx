import { useState, useEffect } from 'react'
import DashboardLayout from '../../components/DashboardLayout'
import * as crm from '../../lib/crmApi'
import { INK, INK_BODY, INK_MUTED, SAGE, AMBER } from '../../theme'
import { Users, UserCheck, Clock, CheckCircle, XCircle, AlertCircle, FileText, Download, Search, Filter, RefreshCw, Eye, Edit3, Trash2, ShieldCheck, Sparkles } from 'lucide-react'

export default function AdminAdmissionPortal() {
  const [stats, setStats] = useState({
    todayRegistrations: 0,
    totalStudents: 0,
    pendingVerification: 0,
    approvedAdmissions: 0,
    rejectedAdmissions: 0,
    totalCounselors: 0,
    documentsPending: 0,
    departmentStats: {}
  })

  const [students, setStudents] = useState([])
  const [counselors, setCounselors] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ search: '', status: '', counselorId: '', department: '' })
  
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [modalType, setModalType] = useState(null)

  async function loadData() {
    setLoading(true)
    try {
      const [sRes, stRes, cRes] = await Promise.all([
        crm.getStudentRegistrationStats(),
        crm.listStudentRegistrations(filters),
        crm.listCounselors()
      ])
      if (sRes.stats) setStats(sRes.stats)
      if (stRes.students) setStudents(stRes.students)
      if (cRes.counselors) setCounselors(cRes.counselors)
    } catch (err) {
      console.error('Failed to load admission portal data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [filters.search, filters.status, filters.counselorId, filters.department])

  async function handleApproveAdmission(studentId) {
    try {
      await crm.updateStudentAdmissionStatus(studentId, { admissionStatus: 'Approved', approvedBy: 'Admin' })
      loadData()
      setSelectedStudent(null)
    } catch (err) {
      alert('Failed to approve admission')
    }
  }

  async function handleRejectAdmission(studentId) {
    const remarks = prompt('Enter reason for rejection:')
    if (remarks === null) return
    try {
      await crm.updateStudentAdmissionStatus(studentId, { admissionStatus: 'Rejected', remarks, approvedBy: 'Admin' })
      loadData()
      setSelectedStudent(null)
    } catch (err) {
      alert('Failed to reject admission')
    }
  }

  async function handleUpdateVerification(studentId, verificationStatus) {
    try {
      await crm.updateStudentVerification(studentId, { verificationStatus })
      loadData()
    } catch (err) {
      alert('Failed to update verification status')
    }
  }

  function exportToCSV() {
    if (!students.length) return
    const headers = ['Registration No', 'Student Name', 'Mobile', 'Email', 'Course', 'Department', 'Counselor ID', 'Counselor Name', 'Registration Date', 'Verification', 'Admission']
    const rows = students.map(s => [
      s.registrationNumber, s.name, s.mobile, s.email, s.courseInterested, s.department, s.counselorId, s.counselorName, s.registrationDate, s.verificationStatus, s.admissionStatus
    ])
    
    let csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `Student_Registrations_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
  }

  return (
    <DashboardLayout activeItem="Admissions Portal">
      <div style={{ padding: '0 0 40px', fontFamily: 'Inter, sans-serif' }}>
        
        {/* Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: INK }}>Real-Time Admission Dashboard</h1>
            <p style={{ color: INK_MUTED, fontSize: 13, margin: '4px 0 0', fontWeight: 500 }}>Live Student Registrations, Document Verification & Counselor Tracking</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={loadData} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#FFF', color: INK_BODY, border: '1px solid #E8E8E8', padding: '9px 16px', borderRadius: 10, cursor: 'pointer', fontSize: 13, fontWeight: 600, boxShadow: '0 2px 6px rgba(0,0,0,0.02)' }}>
              <RefreshCw size={15} /> Refresh Live
            </button>
            <button onClick={exportToCSV} style={{ display: 'flex', alignItems: 'center', gap: 6, background: SAGE, color: '#FFF', border: 'none', padding: '9px 18px', borderRadius: 10, cursor: 'pointer', fontSize: 13, fontWeight: 700, boxShadow: '0 4px 12px rgba(125,155,118,0.25)' }}>
              <Download size={15} /> Export Excel / CSV
            </button>
          </div>
        </div>

        {/* Real-time Metric Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
          <StatCard icon={Clock} title="Today's Registrations" value={stats.todayRegistrations} color="#2563EB" />
          <StatCard icon={Users} title="Total Students" value={stats.totalStudents} color="#4F46E5" />
          <StatCard icon={AlertCircle} title="Pending Verification" value={stats.pendingVerification} color="#D97706" />
          <StatCard icon={CheckCircle} title="Approved Admissions" value={stats.approvedAdmissions} color="#16A34A" />
          <StatCard icon={XCircle} title="Rejected Admissions" value={stats.rejectedAdmissions} color="#DC2626" />
          <StatCard icon={UserCheck} title="Total Counselors" value={stats.totalCounselors} color="#9333EA" />
        </div>

        {/* Live Filter Bar */}
        <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 16, marginBottom: 20, display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
          <div style={{ flex: 1, minWidth: 240, display: 'flex', alignItems: 'center', background: '#FAFAFA', border: '1px solid #E8E8E8', borderRadius: 10, padding: '0 12px' }}>
            <Search size={16} color={INK_MUTED} />
            <input
              type="text"
              placeholder="Search Name, Reg No, Mobile, Counselor..."
              value={filters.search}
              onChange={e => setFilters({ ...filters, search: e.target.value })}
              style={{ width: '100%', background: 'transparent', border: 'none', color: INK, padding: '11px 8px', fontSize: 13, outline: 'none', fontWeight: 500 }}
            />
          </div>

          <select
            value={filters.status}
            onChange={e => setFilters({ ...filters, status: e.target.value })}
            style={selectStyle}
          >
            <option value="">All Admission Statuses</option>
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
          </select>

          <select
            value={filters.counselorId}
            onChange={e => setFilters({ ...filters, counselorId: e.target.value })}
            style={selectStyle}
          >
            <option value="">All Counselors</option>
            {counselors.map(c => (
              <option key={c._id} value={c.counselorId}>{c.counselorId} - {c.name}</option>
            ))}
          </select>
        </div>

        {/* Live Registration Table */}
        <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, overflow: 'hidden', boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#F8FAFC', color: INK_MUTED, borderBottom: '1px solid #E8E8E8' }}>
                <th style={thStyle}>Reg Number</th>
                <th style={thStyle}>Student Name</th>
                <th style={thStyle}>Mobile</th>
                <th style={thStyle}>Course & Dept</th>
                <th style={thStyle}>Assigned Counselor</th>
                <th style={thStyle}>Reg Time</th>
                <th style={thStyle}>Docs Verification</th>
                <th style={thStyle}>Admission Status</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 36, color: INK_MUTED, fontWeight: 500 }}>No student registrations found matching filters.</td>
                </tr>
              ) : (
                students.map(s => (
                  <tr key={s._id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={tdStyle}><strong style={{ color: '#2563EB', fontWeight: 800 }}>{s.registrationNumber}</strong></td>
                    <td style={tdStyle}><span style={{ fontWeight: 700, color: INK }}>{s.name}</span></td>
                    <td style={tdStyle}>{s.mobile}</td>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600, color: INK }}>{s.courseInterested}</div>
                      <div style={{ fontSize: 11, color: INK_MUTED }}>{s.department}</div>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ color: '#D97706', fontWeight: 800 }}>{s.counselorId}</span> ({s.counselorName})
                    </td>
                    <td style={tdStyle}>{s.registrationDate} {s.registrationTime}</td>
                    <td style={tdStyle}>
                      <select
                        value={s.verificationStatus}
                        onChange={e => handleUpdateVerification(s._id, e.target.value)}
                        style={{
                          border: '1px solid #E2E8F0', padding: '4px 8px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                          background: s.verificationStatus === 'Verified' ? '#DCFCE7' : s.verificationStatus === 'Rejected' ? '#FEE2E2' : '#FEF3C7',
                          color: s.verificationStatus === 'Verified' ? '#15803D' : s.verificationStatus === 'Rejected' ? '#991B1B' : '#B45309'
                        }}
                      >
                        <option value="Pending">Pending</option>
                        <option value="Verified">Verified</option>
                        <option value="Missing">Missing Docs</option>
                        <option value="Rejected">Rejected</option>
                      </select>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 800,
                        background: s.admissionStatus === 'Approved' ? '#DCFCE7' : s.admissionStatus === 'Rejected' ? '#FEE2E2' : '#FEF3C7',
                        color: s.admissionStatus === 'Approved' ? '#15803D' : s.admissionStatus === 'Rejected' ? '#991B1B' : '#B45309',
                        border: `1px solid ${s.admissionStatus === 'Approved' ? '#86EFAC' : s.admissionStatus === 'Rejected' ? '#FCA5A5' : '#FDE68A'}`
                      }}>
                        {s.admissionStatus}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button onClick={() => { setSelectedStudent(s); setModalType('view') }} style={actionBtnStyle} title="View Details">
                          <Eye size={14} />
                        </button>
                        {s.admissionStatus !== 'Approved' && (
                          <button onClick={() => handleApproveAdmission(s._id)} style={{ ...actionBtnStyle, background: '#DCFCE7', color: '#15803D', border: '1px solid #86EFAC' }} title="Approve">
                            <CheckCircle size={14} />
                          </button>
                        )}
                        {s.admissionStatus !== 'Rejected' && (
                          <button onClick={() => handleRejectAdmission(s._id)} style={{ ...actionBtnStyle, background: '#FEE2E2', color: '#991B1B', border: '1px solid #FCA5A5' }} title="Reject">
                            <XCircle size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* View Details Modal */}
        {selectedStudent && modalType === 'view' && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99 }}>
            <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 20, width: '90%', maxWidth: 640, maxHeight: '90vh', overflowY: 'auto', padding: 28, boxShadow: '0 20px 50px rgba(0,0,0,0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E8E8E8', paddingBottom: 14, marginBottom: 20 }}>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#2563EB' }}>Student Record: {selectedStudent.registrationNumber}</h3>
                <button onClick={() => setSelectedStudent(null)} style={{ background: 'none', border: 'none', color: INK_MUTED, fontSize: 20, cursor: 'pointer', fontWeight: 800 }}>✕</button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, fontSize: 13, marginBottom: 24, color: INK_BODY }}>
                <div><strong style={{ color: INK }}>Full Name:</strong> {selectedStudent.name}</div>
                <div><strong style={{ color: INK }}>Father Name:</strong> {selectedStudent.fatherName}</div>
                <div><strong style={{ color: INK }}>Mother Name:</strong> {selectedStudent.motherName}</div>
                <div><strong style={{ color: INK }}>DOB / Gender:</strong> {selectedStudent.dob} ({selectedStudent.gender})</div>
                <div><strong style={{ color: INK }}>Aadhaar No:</strong> {selectedStudent.aadhaarNumber}</div>
                <div><strong style={{ color: INK }}>Mobile:</strong> {selectedStudent.mobile}</div>
                <div><strong style={{ color: INK }}>Email:</strong> {selectedStudent.email}</div>
                <div><strong style={{ color: INK }}>City / District:</strong> {selectedStudent.city}, {selectedStudent.district}</div>
                <div><strong style={{ color: INK }}>SSC % / Inter %:</strong> {selectedStudent.sscPercentage}% / {selectedStudent.interPercentage}%</div>
                <div><strong style={{ color: INK }}>Entrance Rank:</strong> {selectedStudent.entranceExam} (Rank: {selectedStudent.rank || 'N/A'})</div>
                <div><strong style={{ color: INK }}>Course:</strong> {selectedStudent.courseInterested}</div>
                <div><strong style={{ color: INK }}>Department:</strong> {selectedStudent.department}</div>
                <div><strong style={{ color: INK }}>Counselor:</strong> {selectedStudent.counselorName} ({selectedStudent.counselorId})</div>
                <div><strong style={{ color: INK }}>Reg Time:</strong> {selectedStudent.registrationDate} {selectedStudent.registrationTime}</div>
              </div>

              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', borderTop: '1px solid #E8E8E8', paddingTop: 18 }}>
                <button onClick={() => handleApproveAdmission(selectedStudent._id)} style={{ background: '#16A34A', color: '#FFF', border: 'none', padding: '10px 20px', borderRadius: 10, fontWeight: 800, cursor: 'pointer' }}>
                  Approve Admission
                </button>
                <button onClick={() => handleRejectAdmission(selectedStudent._id)} style={{ background: '#DC2626', color: '#FFF', border: 'none', padding: '10px 20px', borderRadius: 10, fontWeight: 800, cursor: 'pointer' }}>
                  Reject Admission
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

const selectStyle = {
  background: '#FAFAFA',
  border: '1px solid #E8E8E8',
  color: INK,
  padding: '10px 14px',
  borderRadius: 10,
  fontSize: 13,
  fontWeight: 600,
  outline: 'none'
}

const thStyle = { padding: '14px 16px', fontWeight: 800, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }
const tdStyle = { padding: '14px 16px', color: INK_BODY, fontWeight: 500 }
const actionBtnStyle = { background: '#FAFAFA', border: '1px solid #E8E8E8', color: INK_BODY, padding: '7px 10px', borderRadius: 8, cursor: 'pointer' }
