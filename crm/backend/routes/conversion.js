const express = require('express')
const router = express.Router()

// Mock data & statistical state for live consultative conversion tracking
const abTestingState = {
  opening: {
    name: 'Call Opening Phrase',
    variants: [
      { id: 'A', label: 'Generic Greeting', text: 'Hi! Welcome to Aditya University. How can I help you today?', impressions: 1240, conversions: 310 },
      { id: 'B', label: 'Personalized Score Hook', text: 'Hi! Looking for B.Tech CSE? Great choice! What was your 12th score so I can check your scholarship?', impressions: 1480, conversions: 620 }
    ]
  },
  scholarship: {
    name: 'Scholarship Framing',
    variants: [
      { id: 'A', label: 'Price-Focused', text: 'We have up to 50% merit scholarships available.', impressions: 1120, conversions: 312 },
      { id: 'B', label: 'Savings-Focused', text: 'With your 85% score, you get a 50% scholarship: ₹62.5K/year instead of ₹1.25L.', impressions: 1280, conversions: 563 },
      { id: 'C', label: 'High-Achiever Cohort', text: 'Your 85% score earns a 50% fee waiver (save ₹62.5K/yr) and places you in our top 20% honors batch!', impressions: 1420, conversions: 738 }
    ]
  },
  urgency: {
    name: 'Scarcity & Urgency Framing',
    variants: [
      { id: 'A', label: 'Standard Alert', text: 'Admissions are open, seats are filling fast!', impressions: 980, conversions: 196 },
      { id: 'B', label: 'Seat Scarcity Data', text: '50 CSE seats total, 30 admitted (60%). Only 20 seats remain before March 31 deadline.', impressions: 1190, conversions: 501 },
      { id: 'C', label: 'Mathematical Cutoff Drift', text: 'Last year cutoff was 85%. With trend, expected 87% this year. Securing now locks your scholarship.', impressions: 1350, conversions: 702 }
    ]
  },
  objection: {
    name: 'High Fee Objection Handling',
    variants: [
      { id: 'A', label: 'Defensive Value', text: 'Our fees are very competitive compared to other private institutions.', impressions: 890, conversions: 222 },
      { id: 'B', label: 'Validation + ROI Reframe', text: 'Understood. But with 50% waiver, ₹62.5K/yr is less than hostel costs! ₹12L placement gives ROI in 2 years.', impressions: 1250, conversions: 750 }
    ]
  },
  close: {
    name: 'Application Close',
    variants: [
      { id: 'A', label: 'Direct Pitch', text: 'Would you like to apply now?', impressions: 1050, conversions: 262 },
      { id: 'B', label: 'Frictionless 5-Min + ₹5K Discount', text: 'CSE is a perfect fit. Let us start your 5-minute application right now to lock in your ₹5,000 discount. Ready?', impressions: 1490, conversions: 894 }
    ]
  }
}

// 48-Hour Multi-Channel Nurture Schedule
const nurtureTimeline = [
  { step: 1, time: 'Minute 0', channel: 'In-Call / Instant', icon: 'zap', title: 'Application Submitted or ₹5K Discount Link Sent', detail: 'Instant SMS & WhatsApp delivery with 24-hour validity coupon and secure 5-minute pre-filled application link.' },
  { step: 2, time: 'Hour 2', channel: 'Email', icon: 'mail', title: 'Official Confirmation & Next Steps', detail: 'Welcome packet from Dean of Admissions detailing merit cutoffs, faculty profile, and semester milestones.' },
  { step: 3, time: 'Hour 12', channel: 'WhatsApp', icon: 'message-circle', title: '₹5,000 Early Bird Discount Reminder', detail: 'Automated urgency alert: "Your ₹5,000 application discount expires in 12 hours! Tap to apply: enrolo.io/apply"' },
  { step: 4, time: 'Hour 24', channel: 'SMS', icon: 'bell', title: 'Discount Expiration & Scholarship Grace Period', detail: 'Notice confirming discount expiration but holding 50% merit scholarship reservation for next 48 hours.' },
  { step: 5, time: 'Hour 36', channel: 'Email', icon: 'award', title: 'Home State Alumni Spotlight', detail: 'Success profile of a top engineer from the candidate’s city who graduated and secured ₹18 LPA at Microsoft.' },
  { step: 6, time: 'Hour 48', channel: 'Voice Call (PRIYA)', icon: 'phone-call', title: 'Consultative Follow-up Call', detail: 'Priya checks in: "Hi! Saw you downloaded the brochure. Did you have any questions on the fee schedule or campus hostel?"' }
]

// 1. GET /api/conversion/metrics
router.get('/metrics', (req, res) => {
  const currentBroken = {
    inquiries: 1000,
    answered: 400,
    informed: 150,
    interested: 50,
    submitted: 20,
    admitted: 10,
    conversionRate: 1.0,
    costPerAdmission: 2000000, // ₹20L
    avgTuition: 200000, // ₹2L
    totalRevenue: 2000000 // 10 * ₹2L = ₹20L
  }

  const priyaOptimized = {
    inquiries: 1000,
    answered: 920,
    informed: 850,
    interested: 580,
    submitted: 460,
    admitted: 350,
    conversionRate: 35.0,
    costPerAdmission: 280000, // ₹2.8L
    avgTuition: 200000, // ₹2L
    totalRevenue: 700000000 // 350 * ₹2L = ₹70 Crore
  }

  res.json({
    success: true,
    benchmark: {
      multiplier: '35x',
      revenueImpact: '₹70 Crore',
      costEfficiency: '86% Reduction',
      currentBroken,
      priyaOptimized
    },
    principles: [
      { id: 1, name: 'Perceived Value', impact: '+30% Conversion', desc: 'Candidate feels understood through personalized scholarship math (e.g. 85% = 50% fee waiver = ₹62.5K/yr).' },
      { id: 2, name: 'Reduced Friction', impact: '+25% Completion', desc: 'Conversational 1-question-at-a-time dialogue replaces intimidating 10-field web forms.' },
      { id: 3, name: 'Social Proof + Urgency', impact: '+15% Close Rate', desc: 'Mathematical cutoff trends and real hometown alumni network replace hollow sales hype.' }
    ]
  })
})

// 2. GET /api/conversion/ab-tests
router.get('/ab-tests', (req, res) => {
  const categories = Object.keys(abTestingState).map(key => {
    const item = abTestingState[key]
    const variants = item.variants.map(v => ({
      ...v,
      conversionRate: v.impressions > 0 ? ((v.conversions / v.impressions) * 100).toFixed(1) : '0.0'
    }))

    // Determine winning variant
    let champion = variants[0]
    for (const v of variants) {
      if (parseFloat(v.conversionRate) > parseFloat(champion.conversionRate)) {
        champion = v
      }
    }

    return {
      categoryKey: key,
      categoryName: item.name,
      variants,
      championId: champion.id,
      championRate: champion.conversionRate
    }
  })

  res.json({ success: true, tests: categories })
})

// 3. POST /api/conversion/ab-tests/record
router.post('/ab-tests/record', (req, res) => {
  const { category, variantId, converted } = req.body
  if (!category || !variantId || !abTestingState[category]) {
    return res.status(400).json({ error: 'Invalid category or variant' })
  }

  const found = abTestingState[category].variants.find(v => v.id === variantId)
  if (!found) {
    return res.status(404).json({ error: 'Variant not found' })
  }

  found.impressions += 1
  if (converted) {
    found.conversions += 1
  }

  res.json({ success: true, updated: found })
})

// 4. GET /api/conversion/nurture-timeline
router.get('/nurture-timeline', (req, res) => {
  res.json({ success: true, timeline: nurtureTimeline })
})

// 5. POST /api/conversion/simulate-offer
router.post('/simulate-offer', (req, res) => {
  const { score = 85, board = 'CBSE', city = 'Delhi', branch = 'B.Tech CSE', objection = 'none' } = req.body
  const numScore = parseFloat(score) || 75.0

  let scholarshipPercent = 20
  let annualSavings = 25000
  let standardFee = 125000
  let discountedFee = 100000

  if (numScore >= 90) {
    scholarshipPercent = 100
    annualSavings = 125000
    discountedFee = 0
  } else if (numScore >= 80) {
    scholarshipPercent = 50
    annualSavings = 62500
    discountedFee = 62500
  } else if (numScore >= 70) {
    scholarshipPercent = 25
    annualSavings = 31250
    discountedFee = 93750
  }

  const cityAlumniMap = {
    delhi: 42,
    mumbai: 55,
    bangalore: 78,
    hyderabad: 94,
    vijayawada: 68,
    visakhapatnam: 52,
    chennai: 38,
    pune: 34
  }
  const alumniCount = cityAlumniMap[city.toLowerCase()] || 45

  // Anticipatory objection resolution
  const objectionBattlecards = {
    fee_expensive: 'Understood. But with your 50% scholarship, you pay only ₹62.5K/year—less than a metro hostel. With ₹12L average placement, your entire degree ROI is under 2 years. Plus we offer zero-interest semester installments.',
    want_to_think: 'Of course, take your time! To help you decide: would you like me to share flexible installment options, arrange a 1-on-1 virtual campus walk, or connect you with an alumni mentor from your city?',
    comparing_colleges: 'Comparing is very smart! What matters most to you: hands-on industry labs, our ₹12L placement record, or net tuition fees? If another college is genuinely a better fit, I will gladly tell you.',
    none: 'Candidate profile is strong and qualified. Immediate CTA recommended.'
  }

  const pitchScript = `Hi! With your ${numScore}% ${board} score from ${city}, you qualify for a ${scholarshipPercent}% merit waiver in ${branch}. Your tuition is ₹${discountedFee.toLocaleString()}/year (saving ₹${annualSavings.toLocaleString()}). You will join ${alumniCount} active alumni from ${city} with a 95% placement record. Shall we start your 5-minute application right now to lock in this fee waiver?`

  res.json({
    success: true,
    offer: {
      score: numScore,
      board,
      city,
      branch,
      scholarshipPercent,
      standardFee,
      discountedFee,
      annualSavings,
      alumniInCity: alumniCount,
      pitchScript,
      rebuttal: objectionBattlecards[objection] || objectionBattlecards.none,
      softCloseIncentive: '₹5,000 application discount valid for 24 hours'
    }
  })
})

module.exports = router
