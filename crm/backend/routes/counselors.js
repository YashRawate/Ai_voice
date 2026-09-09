const express = require('express')
const router = express.Router()
const Counselor = require('../models/Counselor')
const User = require('../models/User')
const Organization = require('../models/Organization')
const College = require('../models/College')

// PUBLIC: Validate Admission Counselor ID for the registration form
router.get('/validate/:counselorId', async (req, res) => {
  try {
    const counselorId = String(req.params.counselorId || '').trim().toUpperCase()
    if (!counselorId) {
      return res.status(400).json({ valid: false, message: 'Counselor ID is required' })
    }

    const counselor = await Counselor.findOne({ counselorId, status: 'Active' })
    if (!counselor) {
      return res.status(404).json({ 
        valid: false, 
        message: 'Invalid Admission Counselor ID. Please contact your Admission Counselor.' 
      })
    }

    return res.json({
      valid: true,
      counselorId: counselor.counselorId,
      name: counselor.name,
      department: counselor.department,
      campus: counselor.campus,
      email: counselor.email
    })
  } catch (err) {
    console.error('Error validating counselor:', err)
    return res.status(500).json({ valid: false, message: 'Server validation error' })
  }
})

// LIST Counselors (Admin view)
router.get('/', async (req, res) => {
  try {
    const counselors = await Counselor.find({}).sort({ createdAt: -1 })
    return res.json({ success: true, count: counselors.length, counselors })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to fetch counselors', error: err.message })
  }
})

// CREATE Counselor (Admin)
router.post('/', async (req, res) => {
  try {
    const { counselorId, name, mobile, email, department, campus } = req.body
    if (!counselorId || !name || !mobile || !email) {
      return res.status(400).json({ message: 'counselorId, name, mobile, and email are required' })
    }

    const existing = await Counselor.findOne({ counselorId: String(counselorId).toUpperCase().trim() })
    if (existing) {
      return res.status(400).json({ message: `Counselor ID '${counselorId}' already exists.` })
    }

    // Default org and branch fallback if not provided
    let org = await Organization.findOne({})
    let branch = await College.findOne({})

    const counselor = await Counselor.create({
      orgId: org?._id || new express.Types.ObjectId(),
      branchId: branch?._id || new express.Types.ObjectId(),
      counselorId: String(counselorId).toUpperCase().trim(),
      name,
      mobile,
      email,
      department: department || 'Admissions',
      campus: campus || 'Main Campus',
      status: 'Active'
    })

    return res.status(201).json({ success: true, counselor })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to create counselor', error: err.message })
  }
})

// EDIT/DISABLE Counselor
router.put('/:id', async (req, res) => {
  try {
    const counselor = await Counselor.findByIdAndUpdate(req.params.id, req.body, { new: true })
    if (!counselor) return res.status(404).json({ message: 'Counselor not found' })
    return res.json({ success: true, counselor })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to update counselor', error: err.message })
  }
})

// DELETE Counselor
router.delete('/:id', async (req, res) => {
  try {
    await Counselor.findByIdAndDelete(req.params.id)
    return res.json({ success: true, message: 'Counselor deleted successfully' })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to delete counselor', error: err.message })
  }
})

module.exports = router
