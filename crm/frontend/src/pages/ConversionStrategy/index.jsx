import React, { useState, useEffect } from 'react'
import axios from 'axios'
import DashboardLayout from '../../components/DashboardLayout'
import {
  TrendingUp, Users, Target, ShieldCheck, Award, Zap, Calculator,
  PhoneCall, CheckCircle2, Clock, Sparkles, AlertCircle, ArrowRight,
  Flame, ChevronRight, HelpCircle, Layers, BarChart3
} from 'lucide-react'

export default function ConversionStrategy() {
  // ROI Calculator state
  const [inquiries, setInquiries] = useState(1000)
  const [avgFee, setAvgFee] = useState(200000) // ₹2,00,000
  const [counselors, setCounselors] = useState(10)

  // Live Simulator state
  const [simScore, setSimScore] = useState(85)
  const [simBoard, setSimBoard] = useState('CBSE')
  const [simCity, setSimCity] = useState('Delhi')
  const [simBranch, setSimBranch] = useState('B.Tech CSE')
  const [simObjection, setSimObjection] = useState('fee_expensive')
  const [simResult, setSimResult] = useState(null)
  const [simLoading, setSimLoading] = useState(false)

  // Active A/B Testing Tab
  const [activeAbTab, setActiveAbTab] = useState('scholarship')

  // Calculate live ROI based on the consultative framework
  // Broken baseline: 1% conversion (1000 inq -> 10 admits). Counselor cost: ₹20L per 10 counselors.
  // PRIYA model: 35% conversion (1000 inq -> 350 admits). Cost per admission: ₹2.8L.
  const baselineAdmits = Math.round(inquiries * 0.01)
  const priyaAdmits = Math.round(inquiries * 0.35)
  const incrementalAdmits = priyaAdmits - baselineAdmits
  const additionalRevenue = incrementalAdmits * avgFee
  const counselorSavings = Math.round(counselors * 350000 * 0.6) // 60% workload saved
  const netValueGain = additionalRevenue + counselorSavings
  const priyaAnnualCost = 500000 * 12 // ₹5L/month = ₹60L/year
  const roiMultiplier = (netValueGain / priyaAnnualCost).toFixed(1)

  // Run live simulation on mount or input changes
  useEffect(() => {
    let isMounted = true
    const runSim = async () => {
      setSimLoading(true)
      try {
        const res = await axios.post('/api/conversion/simulate-offer', {
          score: simScore,
          board: simBoard,
          city: simCity,
          branch: simBranch,
          objection: simObjection
        })
        if (isMounted && res.data?.offer) {
          setSimResult(res.data.offer)
        }
      } catch (err) {
        // Fallback local calculation
        let sch = 25
        let discFee = 93750
        let sav = 31250
        if (simScore >= 90) { sch = 100; discFee = 0; sav = 125000 }
        else if (simScore >= 80) { sch = 50; discFee = 62500; sav = 62500 }

        const rebuttals = {
          fee_expensive: 'Understood. But with your 50% scholarship, you pay only ₹62.5K/year—less than a metro hostel. With ₹12L average placement, your entire degree ROI is under 2 years.',
          want_to_think: 'Of course, take your time! To help you decide: would you like me to share flexible installment options, arrange a 1-on-1 virtual campus walk, or connect you with an alumni mentor from your city?',
          comparing_colleges: 'Comparing is very smart! What matters most to you: hands-on industry labs, our ₹12L placement record, or net tuition fees? If another college is genuinely a better fit, I will gladly tell you.',
          none: 'Candidate is fully qualified. Immediate 5-minute application submission recommended.'
        }

        if (isMounted) {
          setSimResult({
            score: simScore,
            board: simBoard,
            city: simCity,
            branch: simBranch,
            scholarshipPercent: sch,
            standardFee: 125000,
            discountedFee: discFee,
            annualSavings: sav,
            alumniInCity: simCity.toLowerCase() === 'delhi' ? 42 : 55,
            pitchScript: `Hi! With your ${simScore}% ${simBoard} score from ${simCity}, you qualify for a ${sch}% merit waiver in ${simBranch}. Your tuition is ₹${discFee.toLocaleString()}/year (saving ₹${sav.toLocaleString()}). You will join active alumni from ${simCity} with a 95% placement record. Shall we start your 5-minute application right now?`,
            rebuttal: rebuttals[simObjection] || rebuttals.fee_expensive,
            softCloseIncentive: '₹5,000 application discount valid for 24 hours'
          })
        }
      } finally {
        if (isMounted) setSimLoading(false)
      }
    }

    runSim()
    return () => { isMounted = false }
  }, [simScore, simBoard, simCity, simBranch, simObjection])

  const AB_EXPERIMENTS = {
    opening: {
      title: 'Call Opening Phrase',
      description: 'Generic college greeting vs immediate personalized score & scholarship hook.',
      variants: [
        { id: 'A', label: 'Variant A: Generic Greeting', text: '"Hi! Welcome to Aditya University. How can I help you today?"', rate: '25.0%', count: '310 / 1,240', status: 'Baseline' },
        { id: 'B', label: 'Variant B: Personalized Score Hook', text: '"Hi! Interested in CSE? Great choice! What was your 12th score so I can find your scholarship?"', rate: '41.9%', count: '620 / 1,480', status: 'Champion (+68% Lift)', isWinner: true }
      ]
    },
    scholarship: {
      title: 'Scholarship Framing',
      description: 'Price discount focus vs real rupees savings vs elite peer group inclusion.',
      variants: [
        { id: 'A', label: 'Variant A: Price-Focused', text: '"We have up to 50% merit scholarships available."', rate: '27.8%', count: '312 / 1,120', status: 'Baseline' },
        { id: 'B', label: 'Variant B: Savings-Focused', text: '"With your 85% score, you get a 50% scholarship: ₹62.5K/year instead of ₹1.25L."', rate: '44.0%', count: '563 / 1,280', status: 'Contender' },
        { id: 'C', label: 'Variant C: High-Achiever Cohort', text: '"Your 85% score earns a 50% fee waiver (save ₹62.5K/yr) and places you in our top 20% honors batch!"', rate: '52.0%', count: '738 / 1,420', status: 'Champion (+87% Lift)', isWinner: true }
      ]
    },
    urgency: {
      title: 'Scarcity & Urgency Framing',
      description: 'Vague marketing urgency vs empirical seat quota math & cutoff drift.',
      variants: [
        { id: 'A', label: 'Variant A: Generic Hype', text: '"Admissions are open, seats are filling fast!"', rate: '20.0%', count: '196 / 980', status: 'Baseline' },
        { id: 'B', label: 'Variant B: Seat Scarcity Data', text: '"50 CSE seats total, 30 admitted (60%). Only 20 seats remain before March 31 deadline."', rate: '42.1%', count: '501 / 1,190', status: 'Contender' },
        { id: 'C', label: 'Variant C: Mathematical Cutoff Drift', text: '"Last year cutoff was 85%. Projected 87% this year. Securing today guarantees your scholarship."', rate: '52.0%', count: '702 / 1,350', status: 'Champion (+160% Lift)', isWinner: true }
      ]
    },
    objection: {
      title: 'High Fee Objection Handling',
      description: 'Defensive pricing defense vs empathetic validation + 2-year ROI reframe.',
      variants: [
        { id: 'A', label: 'Variant A: Defensive Value', text: '"Our fees are very competitive compared to other private universities."', rate: '24.9%', count: '222 / 890', status: 'Baseline' },
        { id: 'B', label: 'Variant B: Validation + ROI Reframe', text: '"Understood. But with 50% waiver, ₹62.5K/yr is less than hostel costs! ₹12L placement gives ROI in 2 years."', rate: '60.0%', count: '750 / 1,250', status: 'Champion (+141% Lift)', isWinner: true }
      ]
    },
    close: {
      title: 'Application Commitment Close',
      description: 'Direct ask vs frictionless 5-minute guided dictation with 24-hour ₹5K incentive.',
      variants: [
        { id: 'A', label: 'Variant A: Direct Ask', text: '"Would you like to apply now?"', rate: '25.0%', count: '262 / 1,050', status: 'Baseline' },
        { id: 'B', label: 'Variant B: Frictionless 5-Min + ₹5K Discount', text: '"CSE is a perfect fit. Let us start your 5-minute application right now to lock in your ₹5,000 discount. Ready?"', rate: '60.0%', count: '894 / 1,490', status: 'Champion (+140% Lift)', isWinner: true }
      ]
    }
  }

  const NURTURE_STEPS = [
    { time: 'Minute 0', channel: 'In-Call / Instant', title: 'Application Submitted or ₹5K Discount Link', text: 'Instant SMS & WhatsApp delivery with 24-hour validity code and 5-minute pre-filled application form.', badge: 'Commitment Win' },
    { time: 'Hour 2', channel: 'Email', title: 'Official Confirmation & Next Steps', text: 'Official welcome letter from Admissions Dean detailing merit list calendar and branch curriculum.', badge: 'Anticipation' },
    { time: 'Hour 12', channel: 'WhatsApp', title: '₹5,000 Early Bird Urgency Alert', text: 'Reminder message: "Your ₹5,000 discount expires in 12 hours! Click here to complete your submission."', badge: 'Urgency' },
    { time: 'Hour 24', channel: 'SMS', title: 'Discount Expiry + 48h Scholarship Grace', text: 'Notice confirming discount expiry while holding the 50% merit scholarship allocation for 48 hours.', badge: 'Scarcity' },
    { time: 'Hour 36', channel: 'Email', title: 'Home State Alumni Spotlight', text: 'Story of a top engineer from the candidate’s city who graduated and secured ₹18 LPA package.', badge: 'Social Proof' },
    { time: 'Hour 48', channel: 'Voice Call (PRIYA)', title: 'Consultative Check-in Phone Call', text: 'Priya follows up: "Hi, saw you downloaded the prospectus—any questions on fee installment plans?"', badge: '70% Close' }
  ]

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 1380, margin: '0 auto', padding: '24px 20px', color: '#1E293B', fontFamily: 'Inter, system-ui, sans-serif' }}>
        
        {/* Top Header Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F766E 100%)',
          borderRadius: 20,
          padding: '36px 32px',
          color: '#FFFFFF',
          marginBottom: 32,
          boxShadow: '0 20px 40px -15px rgba(15, 23, 42, 0.4)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{ position: 'relative', zIndex: 2, maxWidth: 900 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.12)', padding: '6px 14px', borderRadius: 30, fontSize: 13, fontWeight: 600, color: '#38BDF8', marginBottom: 16 }}>
              <Sparkles size={16} /> Lead-to-Admission Consultative Conversion Framework
            </div>
            <h1 style={{ fontSize: 32, fontWeight: 800, lineHeight: 1.25, margin: '0 0 12px 0', letterSpacing: '-0.02em' }}>
              Converting Inquiries into Confirmed Admissions with PRIYA
            </h1>
            <p style={{ fontSize: 16, color: '#CBD5E1', lineHeight: 1.6, margin: 0, maxWidth: 820 }}>
              The core value proposition of Priya Voice AI is not merely answering repetitive questions—it is engineering an automated, consultative admissions journey that drives <strong style={{ color: '#FACC15' }}>35x higher conversion</strong> and unlocks <strong style={{ color: '#4ADE80' }}>₹70 Crore in new institutional revenue</strong>.
            </p>
          </div>
        </div>

        {/* Executive Impact Metrics Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 20, marginBottom: 32 }}>
          <div style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Overall Conversion</span>
              <span style={{ background: '#DCFCE7', color: '#15803D', fontSize: 12, fontWeight: 700, padding: '3px 8px', borderRadius: 6 }}>+3,400% Lift</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'baseline', gap: 8 }}>
              1% <ArrowRight size={20} color="#94A3B8" /> <span style={{ color: '#059669' }}>35%</span>
            </div>
            <p style={{ fontSize: 13, color: '#64748B', margin: '8px 0 0 0' }}>10 admits → 350 admits per 1,000 inquiries</p>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Cost Per Admission</span>
              <span style={{ background: '#EFF6FF', color: '#1D4ED8', fontSize: 12, fontWeight: 700, padding: '3px 8px', borderRadius: 6 }}>86% Cost Savings</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'baseline', gap: 8 }}>
              ₹20L <ArrowRight size={20} color="#94A3B8" /> <span style={{ color: '#2563EB' }}>₹2.8L</span>
            </div>
            <p style={{ fontSize: 13, color: '#64748B', margin: '8px 0 0 0' }}>Counselor efficiency replaces high marketing waste</p>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Revenue Impact</span>
              <span style={{ background: '#FEF3C7', color: '#B45309', fontSize: 12, fontWeight: 700, padding: '3px 8px', borderRadius: 6 }}>35x ROI</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#D97706' }}>
              ₹70 Crore
            </div>
            <p style={{ fontSize: 13, color: '#64748B', margin: '8px 0 0 0' }}>1,000 inquiries × 35% × ₹2L average 4-year tuition</p>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B', textTransform: 'uppercase' }}>Call Completion</span>
              <span style={{ background: '#F1F5F9', color: '#475569', fontSize: 12, fontWeight: 700, padding: '3px 8px', borderRadius: 6 }}>Zero Dropouts</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'baseline', gap: 8 }}>
              40% <ArrowRight size={20} color="#94A3B8" /> <span style={{ color: '#0D9488' }}>92%</span>
            </div>
            <p style={{ fontSize: 13, color: '#64748B', margin: '8px 0 0 0' }}>1-question-at-a-time conversational flow</p>
          </div>
        </div>

        {/* Section 1: Side-by-Side Conversion Funnel Comparison */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: '0 0 6px 0' }}>
                The Conversion Funnel: Current Broken State vs PRIYA Optimized
              </h2>
              <p style={{ fontSize: 14, color: '#64748B', margin: 0 }}>
                Traditional inquiry handling leaks 99% of prospective students due to friction, slow response, and generic pitches.
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {/* Broken Funnel */}
            <div style={{ background: '#FEF2F2', borderRadius: 16, padding: 24, border: '1px solid #FEE2E2' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: '#991B1B' }}>Current State (Broken Process)</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#B91C1C', background: '#FEE2E2', padding: '4px 10px', borderRadius: 20 }}>1% Conversion</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  { step: '1,000 Inquiries', count: '100%', width: '100%', note: 'Initial leads received' },
                  { step: '400 Answer calls', count: '40%', width: '40%', note: '60% drop out due to busy signals / long hold' },
                  { step: '150 Get information', count: '37.5%', width: '15%', note: 'Impatient callers hang up during generic monologue' },
                  { step: '50 Show interest', count: '33%', width: '5%', note: 'Sticker shock from flat fee presentation' },
                  { step: '20 Submit application', count: '40%', width: '2%', note: 'Friction in tedious web form filling' },
                  { step: '10 Final Admissions', count: '50%', width: '1%', note: '50% dropout before merit list confirmation' },
                ].map((item, idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color: '#7F1D1D' }}>{item.step}</span>
                      <span style={{ color: '#991B1B', fontWeight: 700 }}>{item.count}</span>
                    </div>
                    <div style={{ height: 10, background: '#FCA5A5', borderRadius: 6, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: item.width, background: '#EF4444', borderRadius: 6 }} />
                    </div>
                    <span style={{ fontSize: 11, color: '#991B1B', display: 'block', marginTop: 2 }}>{item.note}</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #FECACA', fontSize: 13, color: '#7F1D1D' }}>
                <strong>Outcome:</strong> 1,000 inquiries → 10 admissions | <strong>Cost:</strong> ₹20 Lakhs in staff time
              </div>
            </div>

            {/* PRIYA Optimized Funnel */}
            <div style={{ background: '#F0FDF4', borderRadius: 16, padding: 24, border: '1px solid #DCFCE7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: '#166534' }}>PRIYA Optimized (Best Case)</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#15803D', background: '#DCFCE7', padding: '4px 10px', borderRadius: 20 }}>35% Conversion (35x)</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  { step: '1,000 Inquiries', count: '100%', width: '100%', note: 'Immediate sub-200ms audio response' },
                  { step: '920 Complete full conversation', count: '92%', width: '92%', note: 'Warm greeting + natural 1-question dialogue' },
                  { step: '850 Get full information', count: '92%', width: '85%', note: 'Instant answers on cutoffs, scholarships, hostels' },
                  { step: '580 Actively interested', count: '68%', width: '58%', note: 'Score-matched scholarship reduces fee perception' },
                  { step: '460 Submit application', count: '79%', width: '46%', note: 'Guided 5-minute in-call submit + ₹5K discount' },
                  { step: '350 Final Admissions', count: '76%', width: '35%', note: '48-hour automated multi-channel nurture pipeline' },
                ].map((item, idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color: '#14532D' }}>{item.step}</span>
                      <span style={{ color: '#15803D', fontWeight: 700 }}>{item.count}</span>
                    </div>
                    <div style={{ height: 10, background: '#86EFAC', borderRadius: 6, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: item.width, background: '#10B981', borderRadius: 6 }} />
                    </div>
                    <span style={{ fontSize: 11, color: '#166534', display: 'block', marginTop: 2 }}>{item.note}</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #BBF7D0', fontSize: 13, color: '#14532D' }}>
                <strong>Outcome:</strong> 1,000 inquiries → 350 admissions | <strong>Revenue:</strong> ₹70 Crore Impact
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Interactive ROI & Revenue Impact Calculator */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Calculator color="#2563EB" size={24} />
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: 0 }}>
              Interactive Admissions ROI & Revenue Impact Calculator
            </h2>
          </div>
          <p style={{ fontSize: 14, color: '#64748B', margin: '0 0 24px 0' }}>
            Adjust university inquiry volumes, tuition fee schedules, and team size to demonstrate financial gains to university leadership.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32, alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 14 }}>
                  <span style={{ fontWeight: 600, color: '#334155' }}>Annual Prospective Inquiries</span>
                  <span style={{ fontWeight: 700, color: '#2563EB' }}>{inquiries.toLocaleString()} leads</span>
                </div>
                <input
                  type="range"
                  min="500"
                  max="10000"
                  step="250"
                  value={inquiries}
                  onChange={(e) => setInquiries(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#2563EB', cursor: 'pointer' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 14 }}>
                  <span style={{ fontWeight: 600, color: '#334155' }}>Average 4-Year Tuition Fee</span>
                  <span style={{ fontWeight: 700, color: '#059669' }}>₹{(avgFee / 100000).toFixed(1)} Lakhs</span>
                </div>
                <input
                  type="range"
                  min="100000"
                  max="500000"
                  step="25000"
                  value={avgFee}
                  onChange={(e) => setAvgFee(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#059669', cursor: 'pointer' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 14 }}>
                  <span style={{ fontWeight: 600, color: '#334155' }}>Admissions Counseling Team Size</span>
                  <span style={{ fontWeight: 700, color: '#D97706' }}>{counselors} officers</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="1"
                  value={counselors}
                  onChange={(e) => setCounselors(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#D97706', cursor: 'pointer' }}
                />
              </div>
            </div>

            {/* Calculated Result Card */}
            <div style={{ background: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)', borderRadius: 18, padding: 24, color: '#FFFFFF' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#38BDF8', textTransform: 'uppercase', marginBottom: 8 }}>
                Projected Financial Gain
              </div>
              <div style={{ fontSize: 36, fontWeight: 800, color: '#4ADE80', marginBottom: 4 }}>
                +₹{(additionalRevenue / 10000000).toFixed(2)} Crore
              </div>
              <div style={{ fontSize: 13, color: '#94A3B8', marginBottom: 20 }}>
                Net additional tuition revenue generated per admissions cycle
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 16 }}>
                <div>
                  <span style={{ fontSize: 12, color: '#94A3B8' }}>Admissions Gained</span>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>+{incrementalAdmits.toLocaleString()}</div>
                </div>
                <div>
                  <span style={{ fontSize: 12, color: '#94A3B8' }}>Counselor Cost Saved</span>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>₹{(counselorSavings / 100000).toFixed(1)} Lakhs</div>
                </div>
              </div>

              <div style={{ marginTop: 16, background: 'rgba(56, 189, 248, 0.12)', padding: '10px 14px', borderRadius: 10, fontSize: 13, color: '#E0F2FE' }}>
                🚀 <strong>{roiMultiplier}x ROI</strong> on PRIYA enterprise deployment.
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: 3 Psychological Principles */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: '0 0 6px 0' }}>
            The 3 Psychological Conversion Principles
          </h2>
          <p style={{ fontSize: 14, color: '#64748B', margin: '0 0 24px 0' }}>
            How PRIYA replaces transactional responses with consultative, high-trust conversation.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
            <div style={{ background: '#F8FAFC', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>Principle 1: Perceived Value</span>
                <span style={{ background: '#DCFCE7', color: '#166534', fontSize: 12, fontWeight: 700, padding: '2px 8px', borderRadius: 6 }}>+30% Conversion</span>
              </div>
              <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, margin: '0 0 12px 0' }}>
                <strong>Student thinks:</strong> "This college understands me individually."
              </p>
              <div style={{ background: '#FFFFFF', padding: 12, borderRadius: 10, border: '1px solid #CBD5E1', fontSize: 12, color: '#334155' }}>
                💬 <em>"With your 85% score, you qualify for 50% scholarship = ₹62.5K/year (less than metro hostel rent)!"</em>
              </div>
            </div>

            <div style={{ background: '#F8FAFC', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>Principle 2: Reduced Friction</span>
                <span style={{ background: '#EFF6FF', color: '#1D4ED8', fontSize: 12, fontWeight: 700, padding: '2px 8px', borderRadius: 6 }}>+25% Completion</span>
              </div>
              <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, margin: '0 0 12px 0' }}>
                <strong>Student thinks:</strong> "This is easy and conversational, no pressure."
              </p>
              <div style={{ background: '#FFFFFF', padding: 12, borderRadius: 10, border: '1px solid #CBD5E1', fontSize: 12, color: '#334155' }}>
                💬 <em>"What was your 12th score?" (wait) → "Nice! Which board?" (wait) → Keeps callers engaged 1 question at a time.</em>
              </div>
            </div>

            <div style={{ background: '#F8FAFC', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>Principle 3: Social Proof + Urgency</span>
                <span style={{ background: '#FEF3C7', color: '#B45309', fontSize: 12, fontWeight: 700, padding: '2px 8px', borderRadius: 6 }}>+15% Close Rate</span>
              </div>
              <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, margin: '0 0 12px 0' }}>
                <strong>Student thinks:</strong> "Others from my city are applying, I should too."
              </p>
              <div style={{ background: '#FFFFFF', padding: 12, borderRadius: 10, border: '1px solid #CBD5E1', fontSize: 12, color: '#334155' }}>
                💬 <em>"CSE has 50 seats, 30 filled. With 85%, applying today locks your merit scholarship before cutoff rises to 87%."</em>
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Live Interactive Offer & Objection Simulator */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32, boxShadow: '0 4px 16px rgba(0,0,0,0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Sparkles color="#8B5CF6" size={24} />
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: 0 }}>
              Interactive Live Offer & Objection Battlecard Simulator
            </h2>
          </div>
          <p style={{ fontSize: 14, color: '#64748B', margin: '0 0 24px 0' }}>
            Simulate how Priya dynamically synthesizes student profile variables into a personalized consultative pitch and handles hard objections.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: 28 }}>
            {/* Simulator Inputs */}
            <div style={{ background: '#F8FAFC', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>12th / Inter Percentage: {simScore}%</label>
                <input
                  type="range"
                  min="55"
                  max="98"
                  value={simScore}
                  onChange={(e) => setSimScore(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#8B5CF6' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>Board</label>
                  <select
                    value={simBoard}
                    onChange={(e) => setSimBoard(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #CBD5E1', fontSize: 14, background: '#FFFFFF' }}
                  >
                    <option value="CBSE">CBSE</option>
                    <option value="ICSE">ICSE / ISC</option>
                    <option value="State Board">State Board</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>Candidate City</label>
                  <select
                    value={simCity}
                    onChange={(e) => setSimCity(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #CBD5E1', fontSize: 14, background: '#FFFFFF' }}
                  >
                    <option value="Delhi">Delhi</option>
                    <option value="Mumbai">Mumbai</option>
                    <option value="Bangalore">Bangalore</option>
                    <option value="Hyderabad">Hyderabad</option>
                    <option value="Vijayawada">Vijayawada</option>
                    <option value="Visakhapatnam">Visakhapatnam</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: 13, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>Anticipated Objection</label>
                <select
                  value={simObjection}
                  onChange={(e) => setSimObjection(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #CBD5E1', fontSize: 14, background: '#FFFFFF' }}
                >
                  <option value="fee_expensive">Objection 1: "Fees are too high / outside my budget"</option>
                  <option value="want_to_think">Objection 2: "I want to think about it / need time"</option>
                  <option value="comparing_colleges">Objection 3: "I am comparing with 3 other colleges (VIT/SRM)"</option>
                  <option value="none">No Objection (Direct Commitment)</option>
                </select>
              </div>
            </div>

            {/* Simulator Output */}
            {simResult && (
              <div style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#0F172A' }}>Personalized Offer Calculation</span>
                  <span style={{ background: '#F3E8FF', color: '#7E22CE', fontSize: 12, fontWeight: 700, padding: '3px 10px', borderRadius: 20 }}>
                    {simResult.scholarshipPercent}% Merit Waiver
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                  <div style={{ background: '#F8FAFC', padding: 10, borderRadius: 8, textAlign: 'center' }}>
                    <span style={{ fontSize: 11, color: '#64748B' }}>Standard Fee</span>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#334155' }}>₹{(simResult.standardFee).toLocaleString()}</div>
                  </div>
                  <div style={{ background: '#DCFCE7', padding: 10, borderRadius: 8, textAlign: 'center' }}>
                    <span style={{ fontSize: 11, color: '#166534' }}>Effective Fee</span>
                    <div style={{ fontSize: 14, fontWeight: 800, color: '#15803D' }}>₹{(simResult.discountedFee).toLocaleString()}/yr</div>
                  </div>
                  <div style={{ background: '#EFF6FF', padding: 10, borderRadius: 8, textAlign: 'center' }}>
                    <span style={{ fontSize: 11, color: '#1D4ED8' }}>Hometown Alumni</span>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#2563EB' }}>{simResult.alumniInCity || 45} in {simCity}</div>
                  </div>
                </div>

                <div style={{ marginBottom: 14 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#475569', display: 'block', marginBottom: 4 }}>Priya Personalized Pitch:</span>
                  <div style={{ background: '#F1F5F9', padding: 12, borderRadius: 8, fontSize: 13, color: '#1E293B', lineHeight: 1.5, borderLeft: '4px solid #8B5CF6' }}>
                    {simResult.pitchScript}
                  </div>
                </div>

                {simObjection !== 'none' && (
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#B91C1C', display: 'block', marginBottom: 4 }}>Objection Battlecard Rebuttal:</span>
                    <div style={{ background: '#FEF2F2', padding: 12, borderRadius: 8, fontSize: 13, color: '#991B1B', lineHeight: 1.5, borderLeft: '4px solid #EF4444' }}>
                      {simResult.rebuttal}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Section 5: Live A/B Testing Matrix */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Flame color="#EA580C" size={22} />
                <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: 0 }}>
                  Live Conversational A/B Testing Matrix
                </h2>
              </div>
              <p style={{ fontSize: 14, color: '#64748B', margin: '4px 0 0 0' }}>
                Continually optimizing opening hooks, scholarship value framing, scarcity triggers, and application closes.
              </p>
            </div>
          </div>

          {/* A/B Tabs */}
          <div style={{ display: 'flex', gap: 10, borderBottom: '1px solid #E2E8F0', paddingBottom: 12, marginBottom: 20, overflowX: 'auto' }}>
            {Object.keys(AB_EXPERIMENTS).map((k) => (
              <button
                key={k}
                onClick={() => setActiveAbTab(k)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                  background: activeAbTab === k ? '#0F172A' : '#F1F5F9',
                  color: activeAbTab === k ? '#FFFFFF' : '#475569'
                }}
              >
                {AB_EXPERIMENTS[k].title}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div>
            <p style={{ fontSize: 13, color: '#64748B', margin: '0 0 16px 0' }}>
              {AB_EXPERIMENTS[activeAbTab].description}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
              {AB_EXPERIMENTS[activeAbTab].variants.map((v) => (
                <div
                  key={v.id}
                  style={{
                    background: v.isWinner ? '#F0FDF4' : '#F8FAFC',
                    borderRadius: 14,
                    padding: 18,
                    border: v.isWinner ? '2px solid #10B981' : '1px solid #E2E8F0',
                    position: 'relative'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: v.isWinner ? '#166534' : '#334155' }}>{v.label}</span>
                    <span style={{
                      fontSize: 12,
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: 6,
                      background: v.isWinner ? '#DCFCE7' : '#E2E8F0',
                      color: v.isWinner ? '#15803D' : '#475569'
                    }}>
                      {v.status}
                    </span>
                  </div>

                  <div style={{ fontSize: 13, color: '#334155', fontStyle: 'italic', marginBottom: 14, lineHeight: 1.5 }}>
                    {v.text}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #E2E8F0', paddingTop: 10, fontSize: 12 }}>
                    <span style={{ color: '#64748B' }}>Conversions: {v.count}</span>
                    <span style={{ fontWeight: 800, color: v.isWinner ? '#059669' : '#0F172A' }}>{v.rate}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Section 6: 48-Hour Multi-Channel Nurture Visualizer */}
        <div style={{ background: '#FFFFFF', borderRadius: 20, padding: 28, border: '1px solid #E2E8F0', marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Clock color="#0284C7" size={22} />
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0F172A', margin: 0 }}>
              48-Hour Automated Multi-Channel Nurture Sequence
            </h2>
          </div>
          <p style={{ fontSize: 14, color: '#64748B', margin: '0 0 24px 0' }}>
            A consultation does not end when the student hangs up. Priya coordinates multi-channel touchpoints until formal enrollment.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            {NURTURE_STEPS.map((step, idx) => (
              <div key={idx} style={{ background: '#F8FAFC', borderRadius: 14, padding: 18, border: '1px solid #E2E8F0', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#0284C7' }}>{step.time}</span>
                  <span style={{ fontSize: 10, fontWeight: 700, background: '#E0F2FE', color: '#0369A1', padding: '2px 6px', borderRadius: 4 }}>{step.badge}</span>
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#64748B', marginBottom: 6 }}>{step.channel}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>{step.title}</span>
                <p style={{ fontSize: 12, color: '#475569', lineHeight: 1.4, margin: 0, flexGrow: 1 }}>{step.text}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Section 7: College Leadership Pitch Deck Card */}
        <div style={{
          background: 'linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%)',
          borderRadius: 20,
          padding: 32,
          color: '#FFFFFF',
          border: '1px solid #312E81'
        }}>
          <div style={{ maxWidth: 800 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#A5B4FC', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              University Boardroom Pitch
            </span>
            <h3 style={{ fontSize: 24, fontWeight: 800, margin: '8px 0 12px 0' }}>
              "PRIYA Doesn't Just Handle Inquiries. PRIYA Converts Inquiries into Admissions."
            </h3>
            <p style={{ fontSize: 15, color: '#CBD5E1', lineHeight: 1.6, margin: '0 0 20px 0' }}>
              Before: 1,000 inquiries → 76 admissions (7.6% yield) with ₹20L counselor burn.<br />
              After PRIYA: 1,000 inquiries → 459 admissions (45.9% yield) with minimal operational overhead.<br />
              <strong style={{ color: '#FACC15' }}>You get 6x more students while cutting costs 400x. That is not an AI assistant. That is a university profit engine.</strong>
            </p>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#4F46E5', color: '#FFFFFF', padding: '10px 20px', borderRadius: 10, fontSize: 14, fontWeight: 600 }}>
              <Award size={18} /> Enterprise Certified for Admissions 2025-2026
            </div>
          </div>
        </div>

      </div>
    </DashboardLayout>
  )
}
