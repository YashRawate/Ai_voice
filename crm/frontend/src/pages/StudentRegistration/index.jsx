import { useState, useEffect } from 'react'
import { CheckCircle2, AlertCircle, Upload, ShieldCheck, Award, FileText, Download, Building2, UserCheck, ArrowRight, ArrowLeft, Sparkles, PhoneCall } from 'lucide-react'
import * as crm from '../../lib/crmApi'

export default function StudentRegistration() {
  const [step, setStep] = useState(1)
  
  // Counselor validation state
  const [counselorIdInput, setCounselorIdInput] = useState('')
  const [counselorData, setCounselorData] = useState(null)
  const [counselorError, setCounselorError] = useState('')
  const [counselorValidating, setCounselorValidating] = useState(false)

  // Form state
  const [form, setForm] = useState({
    name: '', fatherName: '', motherName: '', dob: '', gender: 'Male', category: 'General', aadhaarNumber: '', bloodGroup: 'O+',
    mobile: '', altMobile: '', email: '', address: '', city: '', district: '', state: 'Andhra Pradesh', pincode: '',
    sscSchool: '', sscPercentage: '', interCollege: '', interPercentage: '', diplomaDetails: '', entranceExam: 'EAMCET', rank: '', yearOfPassing: '2026',
    courseInterested: 'B.Tech Computer Science (CSE)', department: 'Computer Science & Engineering', preferredCampus: 'Aditya University Surampalem', hostelRequired: 'No', transportRequired: 'No'
  })

  // Documents
  const [docs, setDocs] = useState({
    photoUrl: '', aadhaarUrl: '', sscMemoUrl: '', interMemoUrl: '', tcUrl: '', casteCertUrl: '', incomeCertUrl: '', migrationCertUrl: ''
  })

  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [registeredStudent, setRegisteredStudent] = useState(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const qr = params.get('qr')
    if (qr) {
      crm.logQrScan(qr).catch(() => {})
    }
  }, [])

  async function handleVerifyCounselor() {
    if (!counselorIdInput.trim()) {
      setCounselorError('Please enter an Admission Counselor ID (e.g. AEC001).')
      return
    }
    setCounselorValidating(true)
    setCounselorError('')
    try {
      const res = await crm.validateCounselorId(counselorIdInput.trim())
      if (res.valid) {
        setCounselorData(res)
        setCounselorError('')
      }
    } catch (err) {
      setCounselorData(null)
      setCounselorError(err.response?.data?.message || 'Invalid Admission Counselor ID. Please contact your Admission Counselor.')
    } finally {
      setCounselorValidating(false)
    }
  }

  function handleFileChange(e, docKey) {
    const file = e.target.files?.[0]
    if (file) {
      setDocs(prev => ({ ...prev, [docKey]: URL.createObjectURL(file) }))
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!counselorData) {
      setCounselorError('Invalid Admission Counselor ID. Please contact your Admission Counselor.')
      setStep(1)
      return
    }

    setSubmitting(true)
    setErrorMsg('')
    try {
      const payload = {
        ...form,
        counselorId: counselorData.counselorId,
        documents: docs
      }
      const res = await crm.submitStudentRegistration(payload)
      if (res.success) {
        setRegisteredStudent(res.student)
        setStep(5)
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.message || 'Registration failed. Please verify your details.')
    } finally {
      setSubmitting(false)
    }
  }

  function printAcknowledgement() {
    window.print()
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 50%, #F1F5F9 100%)', color: '#0F172A', padding: '32px 16px', fontFamily: 'Inter, -apple-system, sans-serif' }}>
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        
        {/* Header Branding */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, background: '#FFFFFF', border: '1px solid #E2E8F0', padding: '8px 20px', borderRadius: 999, boxShadow: '0 4px 12px rgba(0,0,0,0.03)', marginBottom: 16 }}>
            <Building2 size={20} color="#2563EB" />
            <span style={{ fontWeight: 800, fontSize: 14, letterSpacing: 0.5, color: '#1E40AF', textTransform: 'uppercase' }}>ADITYA EDUCATIONAL INSTITUTIONS</span>
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 900, color: '#0F172A', letterSpacing: '-0.02em', margin: '4px 0 8px' }}>
            Online Student Admission Portal 2026
          </h1>
          <p style={{ color: '#64748B', fontSize: 15, fontWeight: 500, margin: 0 }}>Fast, Verified & Digitized Paperless Admissions</p>
        </div>

        {/* Success Screen */}
        {step === 5 && registeredStudent && (
          <div style={{ background: '#FFFFFF', border: '1px solid #BBF7D0', borderRadius: 24, padding: 36, boxShadow: '0 20px 40px rgba(34,197,94,0.08)', textAlign: 'center' }}>
            <div style={{ width: 72, height: 72, background: '#DCFCE7', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <CheckCircle2 size={44} color="#16A34A" />
            </div>
            <h2 style={{ fontSize: 26, fontWeight: 800, color: '#15803D', margin: '0 0 8px' }}>Registration Successful!</h2>
            <p style={{ color: '#475569', fontSize: 15, margin: '0 0 28px' }}>Your registration has been submitted and permanently linked to your assigned Admission Counselor.</p>
            
            {/* Download Card */}
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 18, padding: 24, margin: '0 auto 28px', textAlign: 'left', maxWidth: 560 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: 14, marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#64748B', letterSpacing: 0.5 }}>REGISTRATION NUMBER</div>
                  <div style={{ fontSize: 22, fontWeight: 900, color: '#2563EB', letterSpacing: 0.5 }}>{registeredStudent.registrationNumber}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#64748B' }}>DATE & TIME</div>
                  <div style={{ fontSize: 13, color: '#0F172A', fontWeight: 700 }}>{registeredStudent.registrationDate} {registeredStudent.registrationTime}</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 14 }}>
                <div><span style={{ color: '#64748B' }}>Student Name:</span> <br/><strong style={{ color: '#0F172A' }}>{registeredStudent.name}</strong></div>
                <div><span style={{ color: '#64748B' }}>Assigned Counselor:</span> <br/><strong style={{ color: '#D97706' }}>{registeredStudent.counselorName} ({registeredStudent.counselorId})</strong></div>
                <div><span style={{ color: '#64748B' }}>Course Selected:</span> <br/><strong style={{ color: '#0F172A' }}>{registeredStudent.courseInterested}</strong></div>
                <div><span style={{ color: '#64748B' }}>Department:</span> <br/><strong style={{ color: '#0F172A' }}>{registeredStudent.department}</strong></div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button onClick={printAcknowledgement} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#2563EB', color: '#FFF', padding: '14px 28px', borderRadius: 12, fontWeight: 700, border: 'none', cursor: 'pointer', boxShadow: '0 8px 20px rgba(37,99,235,0.25)' }}>
                <Download size={18} /> Download Acknowledgement PDF
              </button>
              <button onClick={() => window.location.reload()} style={{ background: '#FFFFFF', color: '#475569', padding: '14px 24px', borderRadius: 12, fontWeight: 600, border: '1px solid #CBD5E1', cursor: 'pointer' }}>
                Register Another Student
              </button>
            </div>
          </div>
        )}

        {/* Multi-Step Wizard Container */}
        {step < 5 && (
          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 24, padding: '32px 28px', boxShadow: '0 20px 40px rgba(0,0,0,0.04)' }}>
            
            {/* Counselor Validation Banner */}
            <div style={{ background: counselorData ? '#F0FDF4' : '#FFFBEB', border: counselorData ? '1px solid #86EFAC' : '1px solid #FDE68A', borderRadius: 16, padding: 20, marginBottom: 28 }}>
              <div style={{ fontSize: 13, fontWeight: 800, color: counselorData ? '#166534' : '#B45309', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                <UserCheck size={18} /> ADMISSION COUNSELOR VALIDATION (COMPULSORY)
              </div>
              
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="Enter Counselor ID (e.g. AEC001)"
                  value={counselorIdInput}
                  onChange={e => setCounselorIdInput(e.target.value.toUpperCase())}
                  style={{ flex: 1, minWidth: 220, padding: '12px 16px', borderRadius: 10, background: '#FFFFFF', border: '1px solid #CBD5E1', color: '#0F172A', fontWeight: 800, textTransform: 'uppercase', fontSize: 15, outline: 'none' }}
                />
                <button
                  type="button"
                  onClick={handleVerifyCounselor}
                  disabled={counselorValidating}
                  style={{ background: '#2563EB', color: '#FFFFFF', fontWeight: 800, padding: '12px 24px', borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 14 }}
                >
                  {counselorValidating ? 'Verifying...' : 'Verify Counselor ID'}
                </button>
              </div>

              {counselorData && (
                <div style={{ marginTop: 12, fontSize: 14, color: '#15803D', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <ShieldCheck size={18} /> Verified Counselor: <strong>{counselorData.name} ({counselorData.counselorId})</strong> — {counselorData.department}
                </div>
              )}
              {counselorError && (
                <div style={{ marginTop: 12, fontSize: 14, color: '#DC2626', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <AlertCircle size={18} /> {counselorError}
                </div>
              )}
            </div>

            {/* Error Display */}
            {errorMsg && (
              <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#991B1B', padding: '14px 18px', borderRadius: 12, marginBottom: 24, fontSize: 14, fontWeight: 600 }}>
                {errorMsg}
              </div>
            )}

            {/* Step Tabs Header */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 28, background: '#F8FAFC', padding: 6, borderRadius: 14, border: '1px solid #E2E8F0' }}>
              {['1. Personal', '2. Contact', '3. Academic', '4. Course & Docs'].map((label, idx) => {
                const isActive = step === idx + 1
                return (
                  <button
                    key={idx}
                    onClick={() => setStep(idx + 1)}
                    style={{
                      flex: 1, padding: '12px 6px', borderRadius: 10, border: 'none',
                      background: isActive ? '#FFFFFF' : 'transparent',
                      color: isActive ? '#2563EB' : '#64748B',
                      fontWeight: isActive ? 800 : 600, fontSize: 13, cursor: 'pointer',
                      boxShadow: isActive ? '0 4px 12px rgba(0,0,0,0.05)' : 'none',
                      transition: 'all 0.2s'
                    }}
                  >
                    {label}
                  </button>
                )
              })}
            </div>

            <form onSubmit={handleSubmit}>
              {/* STEP 1: Personal Information */}
              {step === 1 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18 }}>
                  <div>
                    <label style={labelStyle}>Full Student Name *</label>
                    <input required type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="Full Name as per SSC" />
                  </div>
                  <div>
                    <label style={labelStyle}>Father Name *</label>
                    <input required type="text" value={form.fatherName} onChange={e => setForm({ ...form, fatherName: e.target.value })} style={inputStyle} placeholder="Father Name" />
                  </div>
                  <div>
                    <label style={labelStyle}>Mother Name *</label>
                    <input required type="text" value={form.motherName} onChange={e => setForm({ ...form, motherName: e.target.value })} style={inputStyle} placeholder="Mother Name" />
                  </div>
                  <div>
                    <label style={labelStyle}>Date of Birth *</label>
                    <input required type="date" value={form.dob} onChange={e => setForm({ ...form, dob: e.target.value })} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Gender *</label>
                    <select value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })} style={inputStyle}>
                      <option>Male</option><option>Female</option><option>Other</option>
                    </select>
                  </div>
                  <div>
                    <label style={labelStyle}>Category *</label>
                    <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} style={inputStyle}>
                      <option>General</option><option>OBC</option><option>SC</option><option>ST</option><option>EWS</option>
                    </select>
                  </div>
                  <div>
                    <label style={labelStyle}>Aadhaar Number (12 Digits) *</label>
                    <input required type="text" value={form.aadhaarNumber} onChange={e => setForm({ ...form, aadhaarNumber: e.target.value })} style={inputStyle} placeholder="12 Digit Aadhaar" />
                  </div>
                  <div>
                    <label style={labelStyle}>Blood Group</label>
                    <input type="text" value={form.bloodGroup} onChange={e => setForm({ ...form, bloodGroup: e.target.value })} style={inputStyle} placeholder="e.g. O+" />
                  </div>
                </div>
              )}

              {/* STEP 2: Contact Details */}
              {step === 2 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18 }}>
                  <div>
                    <label style={labelStyle}>Mobile Number *</label>
                    <input required type="text" value={form.mobile} onChange={e => setForm({ ...form, mobile: e.target.value })} style={inputStyle} placeholder="10 Digit Mobile" />
                  </div>
                  <div>
                    <label style={labelStyle}>Alternate Mobile</label>
                    <input type="text" value={form.altMobile} onChange={e => setForm({ ...form, altMobile: e.target.value })} style={inputStyle} placeholder="Parent Mobile" />
                  </div>
                  <div>
                    <label style={labelStyle}>Email Address *</label>
                    <input required type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} style={inputStyle} placeholder="student@gmail.com" />
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <label style={labelStyle}>Residential Address *</label>
                    <input required type="text" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} style={inputStyle} placeholder="House No, Street Name, Area" />
                  </div>
                  <div>
                    <label style={labelStyle}>City / Town *</label>
                    <input required type="text" value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} style={inputStyle} placeholder="City Name" />
                  </div>
                  <div>
                    <label style={labelStyle}>District *</label>
                    <input required type="text" value={form.district} onChange={e => setForm({ ...form, district: e.target.value })} style={inputStyle} placeholder="District" />
                  </div>
                  <div>
                    <label style={labelStyle}>State *</label>
                    <input required type="text" value={form.state} onChange={e => setForm({ ...form, state: e.target.value })} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Pincode *</label>
                    <input required type="text" value={form.pincode} onChange={e => setForm({ ...form, pincode: e.target.value })} style={inputStyle} placeholder="6 Digit Pincode" />
                  </div>
                </div>
              )}

              {/* STEP 3: Academic Details */}
              {step === 3 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18 }}>
                  <div>
                    <label style={labelStyle}>SSC/10th School Name *</label>
                    <input required type="text" value={form.sscSchool} onChange={e => setForm({ ...form, sscSchool: e.target.value })} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>SSC Percentage / CGPA *</label>
                    <input required type="number" step="0.1" value={form.sscPercentage} onChange={e => setForm({ ...form, sscPercentage: e.target.value })} style={inputStyle} placeholder="e.g. 88.5" />
                  </div>
                  <div>
                    <label style={labelStyle}>Intermediate/12th College *</label>
                    <input required type="text" value={form.interCollege} onChange={e => setForm({ ...form, interCollege: e.target.value })} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Intermediate Percentage *</label>
                    <input required type="number" step="0.1" value={form.interPercentage} onChange={e => setForm({ ...form, interPercentage: e.target.value })} style={inputStyle} placeholder="e.g. 92.0" />
                  </div>
                  <div>
                    <label style={labelStyle}>Entrance Exam</label>
                    <select value={form.entranceExam} onChange={e => setForm({ ...form, entranceExam: e.target.value })} style={inputStyle}>
                      <option>EAMCET</option><option>JEE</option><option>ECET</option><option>POLYCET</option><option>Others</option><option>None</option>
                    </select>
                  </div>
                  <div>
                    <label style={labelStyle}>Entrance Rank</label>
                    <input type="number" value={form.rank} onChange={e => setForm({ ...form, rank: e.target.value })} style={inputStyle} placeholder="e.g. 15420" />
                  </div>
                  <div>
                    <label style={labelStyle}>Year of Passing *</label>
                    <input required type="number" value={form.yearOfPassing} onChange={e => setForm({ ...form, yearOfPassing: e.target.value })} style={inputStyle} />
                  </div>
                </div>
              )}

              {/* STEP 4: Course Selection & Documents */}
              {step === 4 && (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18, marginBottom: 28 }}>
                    <div>
                      <label style={labelStyle}>Course Interested *</label>
                      <select value={form.courseInterested} onChange={e => setForm({ ...form, courseInterested: e.target.value })} style={inputStyle}>
                        <option>B.Tech Computer Science (CSE)</option>
                        <option>B.Tech Artificial Intelligence & Data Science</option>
                        <option>B.Tech Electronics & Communication (ECE)</option>
                        <option>B.Tech Mechanical Engineering</option>
                        <option>MBA (Master of Business Administration)</option>
                        <option>Diploma / Polytechnic</option>
                      </select>
                    </div>
                    <div>
                      <label style={labelStyle}>Department *</label>
                      <select value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} style={inputStyle}>
                        <option>Computer Science & Engineering</option>
                        <option>Electronics & Communication</option>
                        <option>Management Studies</option>
                        <option>Mechanical Engineering</option>
                      </select>
                    </div>
                    <div>
                      <label style={labelStyle}>Preferred Campus *</label>
                      <select value={form.preferredCampus} onChange={e => setForm({ ...form, preferredCampus: e.target.value })} style={inputStyle}>
                        <option>Aditya University Surampalem</option>
                        <option>Aditya Campus Kakinada</option>
                      </select>
                    </div>
                    <div>
                      <label style={labelStyle}>Hostel Required?</label>
                      <select value={form.hostelRequired} onChange={e => setForm({ ...form, hostelRequired: e.target.value })} style={inputStyle}>
                        <option>No</option><option>Yes</option>
                      </select>
                    </div>
                  </div>

                  <h3 style={{ fontSize: 16, fontWeight: 800, color: '#0F172A', marginBottom: 14, borderTop: '1px solid #E2E8F0', paddingTop: 20 }}>Mandatory Documents Upload</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14 }}>
                    {[
                      { key: 'photoUrl', label: 'Student Photo *' },
                      { key: 'aadhaarUrl', label: 'Aadhaar Card *' },
                      { key: 'sscMemoUrl', label: 'SSC 10th Memo *' },
                      { key: 'interMemoUrl', label: '12th Inter Memo *' },
                      { key: 'tcUrl', label: 'Transfer Certificate *' },
                      { key: 'casteCertUrl', label: 'Caste Certificate' },
                      { key: 'incomeCertUrl', label: 'Income Certificate' },
                      { key: 'migrationCertUrl', label: 'Migration Certificate' },
                    ].map(item => (
                      <div key={item.key} style={{ background: '#F8FAFC', border: '1px border-dashed #CBD5E1', borderRadius: 12, padding: 14, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#475569', fontWeight: 700, marginBottom: 8 }}>{item.label}</div>
                        <input type="file" onChange={e => handleFileChange(e, item.key)} style={{ fontSize: 11, color: '#64748B', width: '100%' }} />
                        {docs[item.key] && <div style={{ fontSize: 12, color: '#16A34A', fontWeight: 700, marginTop: 6 }}>✓ Attached</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Controls */}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32, borderTop: '1px solid #E2E8F0', paddingTop: 20 }}>
                {step > 1 ? (
                  <button type="button" onClick={() => setStep(step - 1)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#F1F5F9', color: '#475569', padding: '12px 20px', borderRadius: 10, border: '1px solid #CBD5E1', cursor: 'pointer', fontWeight: 700 }}>
                    <ArrowLeft size={16} /> Previous
                  </button>
                ) : <div />}

                {step < 4 ? (
                  <button type="button" onClick={() => setStep(step + 1)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#2563EB', color: '#FFF', padding: '12px 26px', borderRadius: 10, border: 'none', cursor: 'pointer', fontWeight: 800 }}>
                    Next Step <ArrowRight size={16} />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={submitting}
                    style={{ background: 'linear-gradient(90deg, #16A34A, #15803D)', color: '#FFF', padding: '14px 32px', borderRadius: 12, border: 'none', cursor: 'pointer', fontWeight: 900, fontSize: 15, boxShadow: '0 8px 20px rgba(22,163,74,0.25)' }}
                  >
                    {submitting ? 'Submitting Registration...' : 'Complete & Submit Registration'}
                  </button>
                )}
              </div>

            </form>
          </div>
        )}

      </div>
    </div>
  )
}

const labelStyle = { fontSize: 12, fontWeight: 700, color: '#475569', display: 'block', marginBottom: 6 }
const inputStyle = {
  width: '100%',
  padding: '11px 14px',
  borderRadius: 10,
  background: '#FFFFFF',
  border: '1px solid #CBD5E1',
  color: '#0F172A',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box'
}
