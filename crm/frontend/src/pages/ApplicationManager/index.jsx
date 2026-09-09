import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import {
  Search, Filter, ChevronDown, Upload, Settings, MessageSquare, Mail, Phone,
  CheckCircle2, X, Plus, Play, RefreshCw, Lock, Eye, EyeOff, FileText, Printer,
  Layers, ChevronRight, Check
} from 'lucide-react'

const INITIAL_DUMMY_APPLICATIONS = [
  { _id: 'app-1', name: 'Sager Kapoor', registrationNumber: 'Demo/PGDM/2026/2112', email: 'sager.k@gmail.com', mobile: '+919876543210', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'PGDM Marketing', department: 'Management', interPercentage: 88, sscPercentage: 84, rank: 92, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-2', name: 'Karan Rajpal', registrationNumber: 'Demo/PGDM/2026/2111', email: 'karan.r@gmail.com', mobile: '+919876543211', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'PGDM Finance', department: 'Finance', interPercentage: 91, sscPercentage: 86, rank: 95, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-3', name: 'Jyoti Mehra', registrationNumber: 'Demo/PGDM/2026/2106', email: 'jyoti.m@gmail.com', mobile: '+919876543212', verificationStatus: 'Pending', admissionStatus: 'Pending', courseInterested: 'B.Tech CSE', department: 'Computer Science', interPercentage: 79, sscPercentage: 76, rank: 78, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-4', name: 'Amiy Mishra', registrationNumber: 'Demo/PGDM/2026/2101', email: 'amiy.m@gmail.com', mobile: '+919876543213', verificationStatus: 'Pending', admissionStatus: 'Pending', courseInterested: 'B.Tech ECE', department: 'Electronics', interPercentage: 82, sscPercentage: 80, rank: 84, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-5', name: 'Dhiraj Kumar', registrationNumber: 'Demo/PGDM/2026/2095', email: 'dhiraj.k@gmail.com', mobile: '+919876543214', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'MBA Data Science', department: 'Analytics', interPercentage: 94, sscPercentage: 91, rank: 98, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Offline' },
  { _id: 'app-6', name: 'Siddharth V', registrationNumber: 'Demo/PGDM/2026/2091', email: 'siddharth@gmail.com', mobile: '+919876543215', verificationStatus: 'Pending', admissionStatus: 'Pending', courseInterested: 'B.Tech AI & ML', department: 'AI', interPercentage: 85, sscPercentage: 82, rank: 86, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-7', name: 'Ravi Suman', registrationNumber: 'Demo/PGDM/2026/2089', email: 'ravi.s@gmail.com', mobile: '+919876543216', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'B.Pharm', department: 'Pharmacy', interPercentage: 89, sscPercentage: 85, rank: 90, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-8', name: 'Rahul Patil', registrationNumber: 'Demo/PGDM/2026/2087', email: 'rahul.p@gmail.com', mobile: '+919876543217', verificationStatus: 'Pending', admissionStatus: 'Approved', courseInterested: 'B.Tech Civil', department: 'Civil', interPercentage: 76, sscPercentage: 72, rank: 75, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Offline' },
  { _id: 'app-9', name: 'Shajkar Ali', registrationNumber: 'Demo/PGDM/2026/2080', email: 'shajkar.a@gmail.com', mobile: '+919876543218', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'PGDM HR', department: 'Management', interPercentage: 87, sscPercentage: 83, rank: 89, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Offline' },
  { _id: 'app-10', name: 'Madhumati S', registrationNumber: 'Demo/PGDM/2026/2078', email: 'madhumati@gmail.com', mobile: '+919876543219', verificationStatus: 'Pending', admissionStatus: 'Pending', courseInterested: 'MBA Finance', department: 'Finance', interPercentage: 81, sscPercentage: 78, rank: 81, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-11', name: 'Ashish Sharma', registrationNumber: 'Demo/PGDM/2026/2077', email: 'ashish.s@gmail.com', mobile: '+919876543220', verificationStatus: 'Verified', admissionStatus: 'Approved', courseInterested: 'B.Tech Mechanical', department: 'Mechanical', interPercentage: 84, sscPercentage: 81, rank: 85, formStatus: 'Complete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-12', name: 'Srinivasan A', registrationNumber: 'Demo/PGDM/2026/2069', email: 'srinivasan@gmail.com', mobile: '+919876543221', verificationStatus: 'Pending', admissionStatus: 'Pending', courseInterested: 'B.Tech IT', department: 'Computer Science', interPercentage: 78, sscPercentage: 75, rank: 77, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' },
  { _id: 'app-13', name: 'Anu Kumar', registrationNumber: 'Demo/PGDM/2026/2068', email: 'anu.k@gmail.com', mobile: '+919876543222', verificationStatus: 'Pending', admissionStatus: 'Approved', courseInterested: 'BBA Analytics', department: 'Analytics', interPercentage: 90, sscPercentage: 87, rank: 93, formStatus: 'Incomplete', paymentStatus: 'Payment Approved', paymentMethod: 'Online' }
]

export default function ApplicationManager() {
  const [applications, setApplications] = useState(INITIAL_DUMMY_APPLICATIONS)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  // View state
  const [viewMode, setViewMode] = useState('table') // 'table' | 'quick'
  const [selectedIds, setSelectedIds] = useState([])

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchCriteria, setSearchCriteria] = useState('name')
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false)
  const [matchType, setMatchType] = useState('all') // 'all' | 'any'
  const [filterRows, setFilterRows] = useState([
    { field: 'paymentStatus', operator: 'equals', value: 'Payment Approved' },
    { field: 'sscPercentage', operator: 'greater_than', value: '60' },
    { field: 'interPercentage', operator: 'between', value: '60,80' },
    { field: 'rank', operator: 'greater_than', value: '80' }
  ])

  // Action Menu Popup state
  const [activeActionMenuId, setActiveActionMenuId] = useState(null)

  // Communication & Automation Modal state
  const [commModalOpen, setCommModalOpen] = useState(false)
  const [commTarget, setCommTarget] = useState(null) // applicant object or null for bulk
  const [selectedChannels, setSelectedChannels] = useState(['whatsapp', 'email'])
  const [selectedTemplate, setSelectedTemplate] = useState('welcome_admission')
  const [customMsg, setCustomMsg] = useState('')
  const [automationTrigger, setAutomationTrigger] = useState('instant') // 'instant' | 'scheduled'

  // Bulk Import Modal
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [csvText, setCsvText] = useState('')

  // Mask PII state
  const [piiMasked, setPiiMasked] = useState(true)

  useEffect(() => {
    fetchApplications()
  }, [])

  const fetchApplications = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/unified-crm/applications', { withCredentials: true })
      if (res.data.success && res.data.applications?.length > 0) {
        setApplications(res.data.applications)
      } else {
        setApplications(INITIAL_DUMMY_APPLICATIONS)
      }
    } catch (err) {
      console.error('Failed to fetch applications', err)
      setApplications(INITIAL_DUMMY_APPLICATIONS)
    } finally {
      setLoading(false)
    }
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === applications.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(applications.map(a => a._id))
    }
  }

  const toggleSelectRow = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])
  }

  const maskEmail = (email) => {
    if (!piiMasked) return email
    if (!email) return '**********@gmail.com'
    const parts = email.split('@')
    return '**********@' + (parts[1] || 'gmail.com')
  }

  const maskMobile = (mobile) => {
    if (!piiMasked) return mobile
    return '**********'
  }

  const handleOpenCommModal = (applicant = null) => {
    setCommTarget(applicant)
    setActiveActionMenuId(null)
    setCommModalOpen(true)
  }

  const handleSendAutomation = async () => {
    try {
      setLoading(true)
      const targets = commTarget ? [commTarget] : applications.filter(a => selectedIds.includes(a._id))
      const res = await axios.post('/api/unified-crm/communication/send-automation', {
        targetApplicants: targets,
        channels: selectedChannels,
        templateName: selectedTemplate,
        customMessage: customMsg
      }, { withCredentials: true })

      setMessage(res.data.message)
      setCommModalOpen(false)
    } catch (err) {
      setMessage('Automation dispatch failed: ' + (err.response?.data?.message || err.message))
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
          const p = l.split(',')
          return { name: p[0]?.trim() || 'Walk-In Candidate', phone: p[1]?.trim() || '9876543210', interPercentage: Number(p[2]) || 85, entranceExam: p[3]?.trim() || 'EAMCET', walkIn: true }
        })
      } else {
        items = [
          { name: 'Sager Kapoor', phone: '+919876543210', interPercentage: 88, entranceExam: 'CAT', walkIn: true },
          { name: 'Karan Rajpal', phone: '+919876543211', interPercentage: 91, entranceExam: 'MAT', walkIn: false }
        ]
      }
      const res = await axios.post('/api/unified-crm/bulk-import', { items }, { withCredentials: true })
      setMessage(res.data.message)
      setImportModalOpen(false)
      setCsvText('')
      fetchApplications()
    } catch (err) {
      setMessage('Import error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  // Filter application list by search
  const filteredApplications = applications.filter(app => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      app.name?.toLowerCase().includes(q) ||
      app.registrationNumber?.toLowerCase().includes(q) ||
      app.email?.toLowerCase().includes(q) ||
      app.mobile?.includes(q)
    )
  })

  return (
    <DashboardLayout>
      <div style={{ fontFamily: 'Inter, system-ui, sans-serif', color: '#1F2937', minHeight: '100vh', background: '#F8FAFC', paddingBottom: 60 }}>

        {/* Top Header Controls Bar (Forest Sage Brand Theme) */}
        <div style={{ background: '#FFFFFF', borderBottom: '1px solid #E2E8F0', padding: '16px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#2D3A2B' }}>Application Manager</h1>
              <span style={{ fontSize: 12, background: '#F1F5EE', color: '#4F664A', border: '1px solid #C7D5BD', padding: '2px 9px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 5, fontWeight: 500 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#7D9B76' }} />
                Applied Filter: Default View
              </span>
            </div>

            {/* Right Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <select
                value={searchCriteria}
                onChange={(e) => setSearchCriteria(e.target.value)}
                style={{ border: '1px solid #C7D5BD', borderRadius: 8, padding: '8px 12px', fontSize: 13, background: 'white', color: '#2D3A2B', outline: 'none' }}>
                <option value="name">Select search criteria</option>
                <option value="reg_no">Application No</option>
                <option value="mobile">Mobile Number</option>
                <option value="email">Email Address</option>
              </select>

              <div style={{ position: 'relative', width: 220 }}>
                <Search size={15} color="#7D9B76" style={{ position: 'absolute', left: 10, top: 10 }} />
                <input
                  type="text"
                  placeholder="Search by..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ width: '100%', border: '1px solid #C7D5BD', borderRadius: 8, padding: '7px 10px 7px 32px', fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
                />
              </div>

              <button
                onClick={() => setFilterDrawerOpen(true)}
                style={{ background: '#FFFFFF', border: '1px solid #C7D5BD', color: '#4F664A', padding: '7px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Filter size={15} color="#7D9B76" /> Filter
              </button>

              <button
                onClick={() => setImportModalOpen(true)}
                style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(125,155,118,0.3)' }}>
                <Upload size={15} /> Application Import <ChevronDown size={14} />
              </button>

              <button
                onClick={() => setPiiMasked(!piiMasked)}
                title="Toggle PII Masking"
                style={{ background: piiMasked ? '#F1F5EE' : '#FEF3C7', border: '1px solid #C7D5BD', padding: '7px 10px', borderRadius: 8, cursor: 'pointer' }}>
                {piiMasked ? <EyeOff size={15} color="#7D9B76" /> : <Eye size={15} color="#B45309" />}
              </button>
            </div>
          </div>

          {/* Sub Controls Row: Records count, Table/Quick view toggle, Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ color: '#5A5A5A' }}>Total <strong style={{ color: '#2D3A2B' }}>{filteredApplications.length}</strong> Records</span>

              {/* View Toggle */}
              <div style={{ display: 'flex', background: '#F1F5EE', padding: 2, borderRadius: 8, border: '1px solid #C7D5BD' }}>
                <button
                  onClick={() => setViewMode('table')}
                  style={{
                    border: 'none', padding: '5px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    background: viewMode === 'table' ? '#7D9B76' : 'transparent',
                    color: viewMode === 'table' ? 'white' : '#5A5A5A'
                  }}>
                  Table View
                </button>
                <button
                  onClick={() => setViewMode('quick')}
                  style={{
                    border: 'none', padding: '5px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    background: viewMode === 'quick' ? '#7D9B76' : 'transparent',
                    color: viewMode === 'quick' ? 'white' : '#5A5A5A'
                  }}>
                  Quick View
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#4F664A' }}>
              {selectedIds.length > 0 && (
                <button
                  onClick={() => handleOpenCommModal(null)}
                  style={{ background: '#7D9B76', color: 'white', border: 'none', padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(125,155,118,0.3)' }}>
                  <MessageSquare size={13} /> Send Mail & WhatsApp ({selectedIds.length})
                </button>
              )}
              <span style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>Add/Remove Column <ChevronDown size={14} /></span>
              <span style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>Sort by User Registration Date (Desc) <ChevronDown size={14} /></span>
            </div>
          </div>
        </div>

        {/* Global Alert Notification */}
        {message && (
          <div style={{ margin: '16px 24px 0', background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1E40AF', padding: '12px 16px', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
              <CheckCircle2 size={18} color="#2563EB" /> {message}
            </div>
            <button onClick={() => setMessage('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1E40AF', fontWeight: 700 }}>✕</button>
          </div>
        )}

        {/* Table View (Matching Meritto Design) */}
        <div style={{ padding: '16px 24px' }}>
          <div style={{ background: '#FFFFFF', borderRadius: 10, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', overflow: 'visible' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', color: '#4B5563', fontWeight: 600 }}>
                  <th style={{ padding: '12px 16px', width: 30 }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.length === filteredApplications.length && filteredApplications.length > 0}
                      onChange={toggleSelectAll}
                      style={{ cursor: 'pointer' }}
                    />
                  </th>
                  <th style={{ padding: '12px 16px' }}>Registered Name</th>
                  <th style={{ padding: '12px 16px' }}>Application No</th>
                  <th style={{ padding: '12px 16px' }}>Registered Email</th>
                  <th style={{ padding: '12px 16px' }}>Registered Mobile</th>
                  <th style={{ padding: '12px 16px' }}>Form Status</th>
                  <th style={{ padding: '12px 16px' }}>Payment Status</th>
                  <th style={{ padding: '12px 16px' }}>Payment Method</th>
                  <th style={{ padding: '12px 16px', textAlign: 'center', width: 60 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredApplications.map((app, index) => {
                  const isSelected = selectedIds.includes(app._id)
                  const isMenuOpen = activeActionMenuId === app._id

                  return (
                    <tr
                      key={app._id || index}
                      style={{
                        borderBottom: index < filteredApplications.length - 1 ? '1px solid #F1F5F9' : 'none',
                        background: isSelected ? '#EFF6FF' : 'transparent',
                        transition: 'background 0.15s'
                      }}>
                      <td style={{ padding: '12px 16px' }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelectRow(app._id)}
                          style={{ cursor: 'pointer' }}
                        />
                      </td>

                      {/* Registered Name (Clickable link) */}
                      <td style={{ padding: '12px 16px', fontWeight: 600 }}>
                        <span
                          style={{ color: '#2563EB', cursor: 'pointer', textDecoration: 'none' }}
                          onClick={() => handleOpenCommModal(app)}>
                          {app.name}
                        </span>
                      </td>

                      {/* Application No */}
                      <td style={{ padding: '12px 16px', color: '#4B5563', fontFamily: 'monospace' }}>
                        {app.registrationNumber || `Demo/PGDM/2026/${2000 + index}`}
                      </td>

                      {/* Registered Email (Masked) */}
                      <td style={{ padding: '12px 16px', color: '#6B7280' }}>
                        {maskEmail(app.email)}
                      </td>

                      {/* Registered Mobile with WhatsApp Icon */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#25D366', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Phone size={10} color="white" />
                          </div>
                          <span style={{ color: '#4B5563' }}>{maskMobile(app.mobile)}</span>
                        </div>
                      </td>

                      {/* Form Status */}
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: 12, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                          background: app.verificationStatus === 'Verified' ? '#F0FDF4' : '#FFFBEB',
                          color: app.verificationStatus === 'Verified' ? '#166534' : '#B45309'
                        }}>
                          {app.verificationStatus === 'Verified' ? 'Complete' : 'Incomplete'}
                        </span>
                      </td>

                      {/* Payment Status */}
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#166534' }}>
                          Payment Approved
                        </span>
                      </td>

                      {/* Payment Method */}
                      <td style={{ padding: '12px 16px', color: '#4B5563' }}>
                        {index % 2 === 0 ? 'Online' : 'Offline'}
                      </td>

                      {/* Action Menu Gear Button & Popup Menu */}
                      <td style={{ padding: '12px 16px', textAlign: 'center', position: 'relative' }}>
                        <button
                          onClick={() => setActiveActionMenuId(isMenuOpen ? null : app._id)}
                          style={{ background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: 6, padding: '4px 6px', cursor: 'pointer', color: '#475569' }}>
                          <Settings size={15} />
                        </button>

                        {/* Action Popup Menu (Matching Screenshot 2) */}
                        {isMenuOpen && (
                          <div style={{
                            position: 'absolute', right: 24, top: 40, width: 220, background: '#FFFFFF',
                            border: '1px solid #E2E8F0', borderRadius: 8, boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
                            zIndex: 100, textAlign: 'left', padding: '6px 0'
                          }}>
                            <div
                              onClick={() => handleOpenCommModal(app)}
                              style={{ padding: '8px 16px', fontSize: 13, color: '#4F664A', fontWeight: 600, background: '#F1F5EE', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                              <MessageSquare size={14} /> Communication (Mail & WA)
                            </div>
                            <div style={{ height: 1, background: '#F1F5F9', margin: '4px 0' }} />
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Edit Application</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Print Application</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>View Document</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Fee Payment Details</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Add to List</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Change Application Stage</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Re-assign Application</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>Re-allocate GD-PI</div>
                            <div className="menu-item" style={{ padding: '7px 16px', fontSize: 12, color: '#374151', cursor: 'pointer' }}>View Score Card</div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* MODAL: Email & WhatsApp Communication Automation */}
        {commModalOpen && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: 'white', borderRadius: 12, width: 560, maxWidth: '90%', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>

              {/* Modal Header */}
              <div style={{ background: 'linear-gradient(135deg, #7D9B76, #4F664A)', color: 'white', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16, fontWeight: 700 }}>
                  <MessageSquare size={18} /> Mail & WhatsApp Communication Automation
                </div>
                <button onClick={() => setCommModalOpen(false)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}><X size={18} /></button>
              </div>

              <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ fontSize: 13, color: '#4B5563' }}>
                  Target: <strong>{commTarget ? commTarget.name : `${selectedIds.length || applications.length} Applicants (Broadcast)`}</strong>
                </div>

                {/* Channel Selector */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>Select Communication Channels:</label>
                  <div style={{ display: 'flex', gap: 16 }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedChannels.includes('whatsapp')}
                        onChange={(e) => setSelectedChannels(e.target.checked ? [...selectedChannels, 'whatsapp'] : selectedChannels.filter(c => c !== 'whatsapp'))}
                      />
                      <span style={{ color: '#25D366', fontWeight: 600 }}>WhatsApp Broadcast</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedChannels.includes('email')}
                        onChange={(e) => setSelectedChannels(e.target.checked ? [...selectedChannels, 'email'] : selectedChannels.filter(c => c !== 'email'))}
                      />
                      <span style={{ color: '#4F664A', fontWeight: 600 }}>Email Automation</span>
                    </label>
                  </div>
                </div>

                {/* Template Selector */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>Automation Template:</label>
                  <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    style={{ width: '100%', border: '1px solid #D1D5DB', borderRadius: 8, padding: 10, fontSize: 13, outline: 'none' }}>
                    <option value="welcome_admission">Welcome Admission Kit & Prospectus</option>
                    <option value="fee_nudge">Fee Payment Pending Reminder & Offer Link</option>
                    <option value="doc_verification">Document Verification Request</option>
                    <option value="gdpi_schedule">GD-PI Interview Call Letter</option>
                  </select>
                </div>

                {/* Automation Trigger Mode */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>Trigger Timing:</label>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <button
                      onClick={() => setAutomationTrigger('instant')}
                      style={{
                        flex: 1, padding: 8, borderRadius: 6, border: '1px solid #C7D5BD', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                        background: automationTrigger === 'instant' ? '#F1F5EE' : 'white',
                        color: automationTrigger === 'instant' ? '#4F664A' : '#4B5563'
                      }}>
                      ⚡ Trigger Instantly
                    </button>
                    <button
                      onClick={() => setAutomationTrigger('scheduled')}
                      style={{
                        flex: 1, padding: 8, borderRadius: 6, border: '1px solid #C7D5BD', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                        background: automationTrigger === 'scheduled' ? '#F1F5EE' : 'white',
                        color: automationTrigger === 'scheduled' ? '#4F664A' : '#4B5563'
                      }}>
                      📅 Scheduled Drip Sequence
                    </button>
                  </div>
                </div>

                {/* Custom Message Body */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>Message Body / Additional Notes:</label>
                  <textarea
                    rows={3}
                    placeholder="Dear {{student_name}}, your application {{application_no}} has been updated..."
                    value={customMsg}
                    onChange={(e) => setCustomMsg(e.target.value)}
                    style={{ width: '100%', border: '1px solid #D1D5DB', borderRadius: 8, padding: 10, fontSize: 12, outline: 'none', boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              {/* Modal Footer */}
              <div style={{ background: '#F8FAFC', padding: '12px 20px', borderTop: '1px solid #E2E8F0', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button onClick={() => setCommModalOpen(false)} style={{ background: '#F1F5F9', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                <button
                  onClick={handleSendAutomation}
                  disabled={loading}
                  style={{ background: 'linear-gradient(135deg, #7D9B76, #4F664A)', color: 'white', border: 'none', padding: '8px 18px', borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(125,155,118,0.3)' }}>
                  <Play size={14} /> Dispatch Automation
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SLIDE-OUT FILTER DRAWER ("Filter application by" - Matching Screenshot 3) */}
        {filterDrawerOpen && (
          <div style={{ position: 'fixed', inset: 0, zIndex: 999, display: 'flex', justifyContent: 'flex-end' }}>
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.3)' }} onClick={() => setFilterDrawerOpen(false)} />

            <div style={{
              position: 'relative', width: 440, maxWidth: '90%', background: '#FFFFFF', height: '100vh',
              display: 'flex', flexDirection: 'column', boxShadow: '-10px 0 30px rgba(0,0,0,0.15)', zIndex: 1000
            }}>
              {/* Drawer Header */}
              <div style={{ background: 'linear-gradient(135deg, #7D9B76, #4F664A)', color: 'white', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 16, fontWeight: 700 }}>Filter application by</div>
                <button onClick={() => setFilterDrawerOpen(false)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}><X size={18} /></button>
              </div>

              {/* Drawer Body */}
              <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Match Type */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 13 }}>
                  <span style={{ color: '#374151', fontWeight: 600 }}>Filter applications that match:</span>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                    <input type="radio" name="match" checked={matchType === 'all'} onChange={() => setMatchType('all')} /> All Criteria
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                    <input type="radio" name="match" checked={matchType === 'any'} onChange={() => setMatchType('any')} /> Any Criteria
                  </label>
                </div>

                {/* Filter Rules List (Matching Screenshot 3) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

                  {/* Row 1: Payment Status */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <select style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Payment Status</option>
                    </select>
                    <select style={{ width: 90, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Equals</option>
                    </select>
                    <select style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Payment Approved</option>
                    </select>
                  </div>

                  {/* AND / OR toggle */}
                  <div style={{ textAlign: 'center', margin: '4px 0' }}>
                    <span style={{ background: '#7D9B76', color: 'white', padding: '2px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>AND</span>
                  </div>

                  {/* Row 2: 10th Marks */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <select style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>10th-Obtained% / CGPA</option>
                    </select>
                    <select style={{ width: 110, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Greater than</option>
                    </select>
                    <input type="text" defaultValue="60" style={{ width: 50, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 8px', fontSize: 12 }} />
                  </div>

                  {/* Row 3: 12th Marks */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <select style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>12th-Obtained% / CGPA</option>
                    </select>
                    <select style={{ width: 110, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Between</option>
                    </select>
                    <input type="text" defaultValue="60,80" style={{ width: 60, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 8px', fontSize: 12 }} />
                  </div>

                  {/* Row 4: Composite Score */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <select style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Composite Score</option>
                    </select>
                    <select style={{ width: 110, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 10px', fontSize: 12 }}>
                      <option>Greater than</option>
                    </select>
                    <input type="text" defaultValue="80" style={{ width: 50, border: '1px solid #D1D5DB', borderRadius: 6, padding: '7px 8px', fontSize: 12 }} />
                  </div>

                  <button style={{ color: '#4F664A', background: 'none', border: 'none', fontSize: 13, fontWeight: 600, textAlign: 'left', cursor: 'pointer', marginTop: 6 }}>
                    + Add More
                  </button>
                </div>
              </div>

              {/* Drawer Footer Buttons */}
              <div style={{ borderTop: '1px solid #E2E8F0', padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC' }}>
                <button onClick={() => setFilterDrawerOpen(false)} style={{ background: 'none', border: 'none', color: '#64748B', fontSize: 13, cursor: 'pointer' }}>↺ Reset</button>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={() => setFilterDrawerOpen(false)} style={{ background: '#FFFFFF', border: '1px solid #C7D5BD', padding: '8px 14px', borderRadius: 6, fontSize: 12, cursor: 'pointer', color: '#4F664A' }}>Save Filter</button>
                  <button onClick={() => setFilterDrawerOpen(false)} style={{ background: 'linear-gradient(135deg, #7D9B76, #4F664A)', color: 'white', border: 'none', padding: '8px 18px', borderRadius: 6, fontWeight: 600, fontSize: 12, cursor: 'pointer', boxShadow: '0 2px 8px rgba(125,155,118,0.3)' }}>Save & Next</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: Application Import */}
        {importModalOpen && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
            <div style={{ background: 'white', padding: 20, borderRadius: 12, width: 440, maxWidth: '90%' }}>
              <h3 style={{ marginTop: 0, fontSize: 16, color: '#2D3A2B' }}>Application Import</h3>
              <textarea
                rows={4}
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder="Sager Kapoor, 9876543210, 88, CAT"
                style={{ width: '100%', borderRadius: 6, border: '1px solid #C7D5BD', padding: 8, fontSize: 12, boxSizing: 'border-box' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
                <button onClick={() => setImportModalOpen(false)} style={{ background: '#F3F4F6', border: 'none', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Cancel</button>
                <button onClick={handleBulkImport} style={{ background: 'linear-gradient(135deg, #7D9B76, #4F664A)', color: 'white', border: 'none', padding: '6px 14px', borderRadius: 6, fontWeight: 600, cursor: 'pointer', fontSize: 12, boxShadow: '0 2px 8px rgba(125,155,118,0.3)' }}>Run Import</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </DashboardLayout>
  )
}
