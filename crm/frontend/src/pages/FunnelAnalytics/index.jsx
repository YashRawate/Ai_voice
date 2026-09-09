import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import {
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, Tooltip, Legend, Cell
} from 'recharts'
import { TrendingUp, Users, Target, ShieldCheck, Award } from 'lucide-react'

const DEFAULT_FUNNEL_DATA = [
  { stage: '1. Inquiries', count: 1250, conversion: 100, fill: '#3B82F6' },
  { stage: '2. Applications', count: 840, conversion: 67, fill: '#10B981' },
  { stage: '3. Verified Docs', count: 620, conversion: 50, fill: '#F59E0B' },
  { stage: '4. Fees Paid', count: 510, conversion: 41, fill: '#8B5CF6' },
  { stage: '5. Enrolled LMS', count: 480, conversion: 38, fill: '#7D9B76' }
]

const DEFAULT_LEAD_SOURCES = [
  { name: 'Web Forms', value: 35, count: 437, color: '#2563EB' },
  { name: 'Priya Voice AI', value: 25, count: 312, color: '#7D9B76' },
  { name: 'Campus Walk-Ins', value: 20, count: 250, color: '#F59E0B' },
  { name: 'Meta Facebook Ads', value: 12, count: 150, color: '#1877F2' },
  { name: 'Google Ads', value: 8, count: 101, color: '#EA4335' }
]

const DEFAULT_MONTHLY_TREND = [
  { month: 'Jan', inquiries: 140, applications: 90, enrolled: 50 },
  { month: 'Feb', inquiries: 180, applications: 120, enrolled: 70 },
  { month: 'Mar', inquiries: 210, applications: 150, enrolled: 90 },
  { month: 'Apr', inquiries: 260, applications: 180, enrolled: 110 },
  { month: 'May', inquiries: 310, applications: 220, enrolled: 140 },
  { month: 'Jun', inquiries: 380, applications: 280, enrolled: 190 },
  { month: 'Jul', inquiries: 420, applications: 320, enrolled: 220 }
]

const DEFAULT_COUNSELORS = [
  { name: 'Priya Verma (Head)', assigned: 340, verified: 295, conversionRate: 86, avgResponseHours: 1.2 },
  { name: 'Karthik Officer', assigned: 280, verified: 230, conversionRate: 82, avgResponseHours: 1.5 },
  { name: 'Ananya Sharma', assigned: 250, verified: 198, conversionRate: 79, avgResponseHours: 1.8 },
  { name: 'Rahul Reddy', assigned: 210, verified: 160, conversionRate: 76, avgResponseHours: 2.1 },
  { name: 'Sneha Patel', assigned: 170, verified: 132, conversionRate: 77, avgResponseHours: 2.0 }
]

const DEFAULT_DEPT_DEMAND = [
  { department: 'Computer Science (CSE)', capacity: 250, applications: 340, enrolled: 235 },
  { department: 'Electronics (ECE)', capacity: 180, applications: 210, enrolled: 165 },
  { department: 'Data Science & AI', capacity: 150, applications: 190, enrolled: 138 },
  { department: 'MBA Management', capacity: 120, applications: 160, enrolled: 112 },
  { department: 'Pharmacy (B.Pharm)', capacity: 100, applications: 130, enrolled: 90 }
]

const DEFAULT_PREDICTIVE = {
  predictions: {
    forecastYield: 68.2,
    predictedEnrollments: 950,
    dropOutRiskPercentage: 12.4,
    recommendedAction: 'High demand predicted for CSE & Data Science. Increase counselor quota by 15%.'
  }
}

export default function FunnelAnalytics() {
  const [funnelData, setFunnelData] = useState(DEFAULT_FUNNEL_DATA)
  const [leadSources, setLeadSources] = useState(DEFAULT_LEAD_SOURCES)
  const [monthlyTrend, setMonthlyTrend] = useState(DEFAULT_MONTHLY_TREND)
  const [counselors, setCounselors] = useState(DEFAULT_COUNSELORS)
  const [deptDemand, setDeptDemand] = useState(DEFAULT_DEPT_DEMAND)
  const [predictive, setPredictive] = useState(DEFAULT_PREDICTIVE)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [fRes, pRes] = await Promise.all([
        axios.get('/api/unified-crm/analytics/funnel', { withCredentials: true }),
        axios.get('/api/unified-crm/predictive/insights', { withCredentials: true })
      ])
      if (fRes.data.success) {
        if (fRes.data.funnel?.length) setFunnelData(fRes.data.funnel)
        if (fRes.data.leadSources?.length) setLeadSources(fRes.data.leadSources)
        if (fRes.data.monthlyTrend?.length) setMonthlyTrend(fRes.data.monthlyTrend)
        if (fRes.data.counselorPerformance?.length) setCounselors(fRes.data.counselorPerformance)
        if (fRes.data.departmentDemand?.length) setDeptDemand(fRes.data.departmentDemand)
      }
      if (pRes.data?.success && pRes.data.predictions) setPredictive(pRes.data)
    } catch (err) {
      console.error('Error loading analytics, using default datasets', err)
    } finally {
      setLoading(false)
    }
  }

  const PIE_COLORS = ['#3D4F3A', '#4F664A', '#647F5E', '#7D9B76', '#8FAC81']

  return (
    <DashboardLayout>
      <div style={{ fontFamily: 'Inter, system-ui, sans-serif', color: '#1F2937', minHeight: '100vh', background: '#F8FAFC', paddingBottom: 60 }}>

        {/* Header Title */}
        <div style={{ background: '#FFFFFF', borderBottom: '1px solid #E2E8F0', padding: '20px 28px', marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#2D3A2B' }}>
            Admissions Funnel & Analytics Dashboard
          </h1>
          <p style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>
            In-depth visual analytics on lead sources, conversion stages, monthly trends, counselor performance SLA, and department yield.
          </p>
        </div>

        <div style={{ maxWidth: 1240, margin: '0 auto', padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* Top KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Total Inquiries</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#4F664A', marginTop: 6 }}>1,250</div>
              <div style={{ fontSize: 12, color: '#4F664A', marginTop: 4, fontWeight: 500 }}>↑ +18% vs last cycle</div>
            </div>

            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Applications Submitted</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#647F5E', marginTop: 6 }}>840</div>
              <div style={{ fontSize: 12, color: '#647F5E', marginTop: 4, fontWeight: 500 }}>67% inquiry conversion</div>
            </div>

            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Verified & Fees Paid</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7D9B76', marginTop: 6 }}>510</div>
              <div style={{ fontSize: 12, color: '#7D9B76', marginTop: 4, fontWeight: 500 }}>₹51,00,000 revenue</div>
            </div>

            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>LMS Enrolled Roster</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#8FAC81', marginTop: 6 }}>480</div>
              <div style={{ fontSize: 12, color: '#8FAC81', marginTop: 4, fontWeight: 500 }}>Canvas LMS Active</div>
            </div>
          </div>

          {/* Row 1: Funnel Bar Chart + Lead Source Pie Chart */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 20 }}>

            {/* Chart 1: 3D Visual Light Pastel Funnel Chart */}
            <div style={{ background: '#FFFFFF', padding: 22, borderRadius: 14, border: '1px solid #E2E8F0', boxShadow: '0 8px 24px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#2D3A2B' }}>
                  5-Stage Admissions Conversion Funnel (3D)
                </h3>
                <span style={{ fontSize: 11, background: '#F1F5EE', color: '#4F664A', padding: '3px 8px', borderRadius: 12, fontWeight: 600 }}>
                  Forest Sage Theme
                </span>
              </div>

              {/* 3D Inverted Forest Sage Funnel */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, width: '100%', padding: '12px 0' }}>
                {[
                  { stage: '1. Inquiries', count: 1250, conversion: '100%', bgTop: '#F1F5EE', bgBase: '#C7D5BD', textCol: '#2D3A2B', rimCol: '#A6BC97', widthPct: 100, dropRate: '67.2% conversion' },
                  { stage: '2. Applications', count: 840, conversion: '67.2%', bgTop: '#E0E9DA', bgBase: '#A6BC97', textCol: '#2D3A2B', rimCol: '#8FAC81', widthPct: 84, dropRate: '73.8% verification' },
                  { stage: '3. Verified Docs', count: 620, conversion: '50.4%', bgTop: '#C7D5BD', bgBase: '#8FAC81', textCol: '#2D3A2B', rimCol: '#7D9B76', widthPct: 68, dropRate: '82.3% fee paid' },
                  { stage: '4. Fees Paid', count: 510, conversion: '41.2%', bgTop: '#A6BC97', bgBase: '#7D9B76', textCol: '#FFFFFF', rimCol: '#647F5E', widthPct: 52, dropRate: '94.1% enrolled' },
                  { stage: '5. Enrolled LMS', count: 480, conversion: '38.4%', bgTop: '#7D9B76', bgBase: '#4F664A', textCol: '#FFFFFF', rimCol: '#3D4F3A', widthPct: 36, dropRate: 'Final Roster' }
                ].map((st, idx, arr) => (
                  <React.Fragment key={idx}>

                    {/* 3D Funnel Level Container */}
                    <div style={{
                      width: `${st.widthPct}%`,
                      position: 'relative',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                    }}>
                      {/* 3D Top Elliptical Rim Overlay */}
                      <div style={{
                        height: 14,
                        width: '100%',
                        background: st.rimCol,
                        borderRadius: '50%',
                        position: 'absolute',
                        top: -7,
                        left: 0,
                        zIndex: 3,
                        boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.7), 0 2px 4px rgba(0,0,0,0.06)'
                      }} />

                      {/* 3D Trapezoid Body */}
                      <div style={{
                        background: `linear-gradient(180deg, ${st.bgTop} 0%, ${st.bgBase} 100%)`,
                        color: st.textCol,
                        padding: '14px 22px 12px 22px',
                        borderRadius: '4px 4px 12px 12px',
                        boxShadow: 'inset 0 3px 6px rgba(255,255,255,0.9), inset 0 -4px 8px rgba(0,0,0,0.05), 0 8px 18px rgba(0,0,0,0.06)',
                        border: `1px solid ${st.rimCol}`,
                        display: 'flex',
                        justify: 'space-between',
                        alignItems: 'center',
                        position: 'relative',
                        zIndex: 2,
                        clipPath: idx === 0
                          ? 'polygon(0% 0%, 100% 0%, 96% 100%, 4% 100%)'
                          : idx === arr.length - 1
                            ? 'polygon(4% 0%, 96% 0%, 90% 100%, 10% 100%)'
                            : 'polygon(3% 0%, 97% 0%, 94% 100%, 6% 100%)'
                      }}>
                        <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: 0.3 }}>{st.stage}</span>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 16, fontWeight: 800 }}>{st.count.toLocaleString()}</span>
                          <span style={{
                            fontSize: 11, background: 'rgba(255,255,255,0.85)', color: st.textCol,
                            padding: '2px 9px', borderRadius: 12, fontWeight: 700, boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
                          }}>
                            {st.conversion}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 3D Drop-off Indicator */}
                    {idx < arr.length - 1 && (
                      <div style={{ fontSize: 11, color: '#059669', fontWeight: 700, margin: '-2px 0', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '1px 8px', borderRadius: 10 }}>
                          ↓ {st.dropRate}
                        </span>
                      </div>
                    )}

                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Chart 2: Lead Source Attribution Pie Chart */}
            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0', color: '#111827' }}>
                Lead Source Attribution Share
              </h3>
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={leadSources} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={(e) => `${e.name}: ${e.value}%`}>
                      {leadSources.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color || PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(val) => [`${val}% Share`, 'Attribution']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>

          {/* Row 2: Monthly Admissions Trend Line/Area Chart */}
          <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0', color: '#111827' }}>
              Monthly Admissions & Enrollment Growth (Jan – Jul 2026)
            </h3>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyTrend} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <XAxis dataKey="month" stroke="#6B7280" fontSize={12} />
                  <YAxis stroke="#6B7280" fontSize={12} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="inquiries" stroke="#2563EB" fill="#3B82F620" name="Inquiries" />
                  <Area type="monotone" dataKey="applications" stroke="#10B981" fill="#10B98120" name="Applications" />
                  <Area type="monotone" dataKey="enrolled" stroke="#7D9B76" fill="#7D9B7620" name="Enrolled" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Row 3: Counselor Performance SLA + Department Demand Forecast */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Chart 4: Counselor SLA & Conversion Bar Chart */}
            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0', color: '#111827' }}>
                Counselor Lead Conversion & SLA Response
              </h3>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={counselors} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <XAxis dataKey="name" stroke="#6B7280" fontSize={10} interval={0} angle={-15} textAnchor="end" />
                    <YAxis stroke="#6B7280" fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="assigned" fill="#94A3B8" name="Assigned" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="verified" fill="#10B981" name="Verified" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 5: Department Demand vs Capacity */}
            <div style={{ background: '#FFFFFF', padding: 20, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0', color: '#111827' }}>
                Department Demand vs Seat Capacity
              </h3>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={deptDemand} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <XAxis dataKey="department" stroke="#6B7280" fontSize={10} interval={0} angle={-15} textAnchor="end" />
                    <YAxis stroke="#6B7280" fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="capacity" fill="#CBD5E1" name="Seat Capacity" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="enrolled" fill="#7D9B76" name="Enrolled" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>

          {/* AI Predictive Insight Banner */}
          {predictive && (
            <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', padding: 18, borderRadius: 12, color: '#1E40AF', fontSize: 14 }}>
              💡 <strong>AI Predictive Yield Insight:</strong> Forecasted Cycle Yield is <strong>{predictive.predictions.forecastYield}%</strong> with <strong>{predictive.predictions.predictedEnrollments} predicted enrollments</strong>. High demand for CSE & Data Science.
            </div>
          )}

        </div>
      </div>
    </DashboardLayout>
  )
}
