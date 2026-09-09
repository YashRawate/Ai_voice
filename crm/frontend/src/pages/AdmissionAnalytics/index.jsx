import { useState, useEffect } from 'react'
import DashboardLayout from '../../components/DashboardLayout'
import * as crm from '../../lib/crmApi'
import { INK, INK_BODY, INK_MUTED, SAGE } from '../../theme'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, Legend } from 'recharts'
import { BarChart3, TrendingUp, PieChart as PieIcon, Award, Users } from 'lucide-react'

// Harmonious pastel color palette matching CRM Analytics
const COLORS = ['#7D9B76', '#818CF8', '#C8923A', '#38BDF8', '#F87171', '#C084FC']
const TOOLTIP_STYLE = { background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 10, color: INK, boxShadow: '0 8px 24px rgba(0,0,0,0.08)', fontSize: 12 }

export default function AdmissionAnalytics() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    crm.listStudentRegistrations().then(res => {
      if (res.students) setStudents(res.students)
    }).catch(console.error)
  }, [])

  const deptMap = {}
  const categoryMap = {}
  const counselorMap = {}
  const genderMap = {}

  students.forEach(s => {
    deptMap[s.department] = (deptMap[s.department] || 0) + 1
    categoryMap[s.category] = (categoryMap[s.category] || 0) + 1
    const cKey = `${s.counselorId} (${s.counselorName})`
    counselorMap[cKey] = (counselorMap[cKey] || 0) + 1
    genderMap[s.gender] = (genderMap[s.gender] || 0) + 1
  })

  const deptData = Object.keys(deptMap).map(k => ({ name: k, count: deptMap[k] }))
  const categoryData = Object.keys(categoryMap).map(k => ({ name: k, count: categoryMap[k] }))
  const counselorData = Object.keys(counselorMap).map(k => ({ name: k, count: counselorMap[k] }))
  const genderData = Object.keys(genderMap).map(k => ({ name: k, count: genderMap[k] }))

  return (
    <DashboardLayout activeItem="Admission Analytics">
      <div style={{ padding: '0 0 40px', fontFamily: 'Inter, sans-serif' }}>
        
        {/* Header Bar */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: INK }}>Admission Analytics & Demographics</h1>
          <p style={{ color: INK_MUTED, fontSize: 13, margin: '4px 0 0', fontWeight: 500 }}>Visual Intelligence on Department Breakdown, Counselor Performance, and Student Demographics</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 20 }}>
          
          {/* Chart 1: Department Distribution */}
          <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 16px', color: INK, display: 'flex', alignItems: 'center', gap: 8 }}>
              <PieIcon size={18} color="#2563EB" /> Department-wise Admissions
            </h3>
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={deptData} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={85} label>
                    {deptData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Top Performing Counselors */}
          <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 16px', color: INK, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Award size={18} color="#818CF8" /> Top Performing Counselors
            </h3>
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={counselorData}>
                  <XAxis dataKey="name" stroke={INK_MUTED} fontSize={11} />
                  <YAxis stroke={INK_MUTED} fontSize={11} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill="#818CF8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Category Distribution */}
          <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 16px', color: INK, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Users size={18} color="#16A34A" /> Social Category Breakdown
            </h3>
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData}>
                  <XAxis dataKey="name" stroke={INK_MUTED} fontSize={11} />
                  <YAxis stroke={INK_MUTED} fontSize={11} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill="#16A34A" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 4: Gender Distribution */}
          <div style={{ background: '#FFF', border: '1px solid #E8E8E8', borderRadius: 16, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 16px', color: INK, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart3 size={18} color="#D97706" /> Gender Distribution
            </h3>
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={genderData} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={85} label>
                    {genderData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>
    </DashboardLayout>
  )
}
