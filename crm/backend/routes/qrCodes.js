const express = require('express')
const router = express.Router()
const QRCodeCampaign = require('../models/QRCodeCampaign')
const Organization = require('../models/Organization')
const College = require('../models/College')

// LIST QR Code Campaigns
router.get('/', async (req, res) => {
  try {
    const campaigns = await QRCodeCampaign.find({}).sort({ createdAt: -1 })
    const formatted = campaigns.map(c => {
      const convRate = c.scansCount > 0 
        ? ((c.successfulRegistrations / c.scansCount) * 100).toFixed(1) 
        : 0
      return {
        ...c._doc,
        conversionRate: `${convRate}%`
      }
    })
    return res.json({ success: true, count: formatted.length, campaigns: formatted })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to fetch QR campaigns', error: err.message })
  }
})

// GENERATE New QR Campaign
router.post('/', async (req, res) => {
  try {
    const { title, code, collegeName, department, campus, campaignName, targetUrl } = req.body
    if (!title || !code) {
      return res.status(400).json({ message: 'title and code are required' })
    }

    const cleanCode = String(code).toUpperCase().trim()
    const existing = await QRCodeCampaign.findOne({ code: cleanCode })
    if (existing) {
      return res.status(400).json({ message: `QR Code '${cleanCode}' already exists` })
    }

    let org = await Organization.findOne({})
    let branch = await College.findOne({})

    const campaign = await QRCodeCampaign.create({
      orgId: org?._id || new express.Types.ObjectId(),
      branchId: branch?._id || new express.Types.ObjectId(),
      title,
      code: cleanCode,
      collegeName: collegeName || 'Aditya University',
      department: department || 'General Admissions',
      campus: campus || 'Main Campus',
      campaignName: campaignName || 'Admissions 2026',
      targetUrl: targetUrl || `http://localhost:5173/student-register?qr=${cleanCode}`
    })

    return res.status(201).json({ success: true, campaign })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to create QR campaign', error: err.message })
  }
})

// LOG Scan Hit
router.post('/:code/scan', async (req, res) => {
  try {
    const campaign = await QRCodeCampaign.findOne({ code: String(req.params.code).toUpperCase() })
    if (campaign) {
      campaign.scansCount += 1
      await campaign.save()
    }
    return res.json({ success: true })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to log scan', error: err.message })
  }
})

module.exports = router
