const express = require('express')
const router = express.Router()
const StudentRegistration = require('../models/StudentRegistration')
const Counselor = require('../models/Counselor')
const Organization = require('../models/Organization')
const College = require('../models/College')
const QRCodeCampaign = require('../models/QRCodeCampaign')

// Utility to generate unique Registration Number: AEC2026-XXXXXX
async function generateRegistrationNumber() {
  const year = new Date().getFullYear()
  const randomDigits = Math.floor(100000 + Math.random() * 900000)
  return `AEC${year}-${randomDigits}`
}

// PUBLIC: Submit Student Registration Form
router.post('/submit', async (req, res) => {
  try {
    const {
      counselorId,
      name, fatherName, motherName, dob, gender, category, aadhaarNumber, bloodGroup,
      mobile, altMobile, email, address, city, district, state, pincode,
      sscSchool, sscPercentage, interCollege, interPercentage, diplomaDetails,
      entranceExam, rank, yearOfPassing,
      courseInterested, department, preferredCampus, hostelRequired, transportRequired,
      documents, campaignCode
    } = req.body

    // Step 1: Validate required fields
    if (!counselorId || !name || !fatherName || !motherName || !dob || !gender || !aadhaarNumber ||
        !mobile || !email || !address || !city || !district || !state || !pincode ||
        !sscSchool || !sscPercentage || !interCollege || !interPercentage || !yearOfPassing ||
        !courseInterested || !department || !preferredCampus) {
      return res.status(400).json({ 
        success: false, 
        message: 'Please fill all mandatory fields across all registration sections.' 
      })
    }

    // Step 2: Validate Admission Counselor ID
    const cleanCounselorId = String(counselorId).trim().toUpperCase()
    const counselor = await Counselor.findOne({ counselorId: cleanCounselorId, status: 'Active' })
    if (!counselor) {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid Admission Counselor ID. Please contact your Admission Counselor.' 
      })
    }

    // Step 3: Duplicate Validation (Check Mobile, Email, Aadhaar)
    const duplicate = await StudentRegistration.findOne({
      $or: [
        { mobile: String(mobile).trim() },
        { email: String(email).trim().toLowerCase() },
        { aadhaarNumber: String(aadhaarNumber).trim() }
      ]
    })

    if (duplicate) {
      let field = 'mobile/email/Aadhaar'
      if (duplicate.mobile === String(mobile).trim()) field = 'Mobile Number'
      else if (duplicate.email === String(email).trim().toLowerCase()) field = 'Email Address'
      else if (duplicate.aadhaarNumber === String(aadhaarNumber).trim()) field = 'Aadhaar Number'

      return res.status(409).json({
        success: false,
        message: `This student is already registered. (Matched by ${field}: ${duplicate.registrationNumber})`
      })
    }

    // Generate unique Registration Number
    const regNo = await generateRegistrationNumber()
    const now = new Date()
    const regDate = now.toISOString().split('T')[0]
    const regTime = now.toTimeString().split(' ')[0]

    // Default Org & Branch
    let org = await Organization.findOne({})
    let branch = await College.findOne({})

    // Check QR campaign linkage
    let qrCampaign = null
    if (campaignCode) {
      qrCampaign = await QRCodeCampaign.findOne({ code: String(campaignCode).toUpperCase() })
      if (qrCampaign) {
        qrCampaign.successfulRegistrations += 1
        await qrCampaign.save()
      }
    }

    // Save Student Record
    const student = await StudentRegistration.create({
      orgId: org?._id || new express.Types.ObjectId(),
      branchId: branch?._id || new express.Types.ObjectId(),
      registrationNumber: regNo,

      counselorId: counselor.counselorId,
      counselorName: counselor.name,
      registrationDate: regDate,
      registrationTime: regTime,

      name, fatherName, motherName, dob, gender,
      category: category || 'General',
      aadhaarNumber: String(aadhaarNumber).trim(),
      bloodGroup: bloodGroup || 'O+',

      mobile: String(mobile).trim(),
      altMobile: altMobile ? String(altMobile).trim() : '',
      email: String(email).trim().toLowerCase(),
      address, city, district, state, pincode,

      sscSchool, sscPercentage: Number(sscPercentage),
      interCollege, interPercentage: Number(interPercentage),
      diplomaDetails: diplomaDetails || '',
      entranceExam: entranceExam || 'EAMCET',
      rank: Number(rank) || 0,
      yearOfPassing: Number(yearOfPassing),

      courseInterested, department, preferredCampus,
      hostelRequired: hostelRequired || 'No',
      transportRequired: transportRequired || 'No',

      documents: documents || {},
      verificationStatus: 'Pending',
      admissionStatus: 'Pending',
      qrCampaignId: qrCampaign?._id || null
    })

    // Emit Socket.IO real-time event if io is attached
    const io = req.app.get('io')
    if (io) {
      io.emit('student_registered', {
        studentId: student._id,
        registrationNumber: student.registrationNumber,
        name: student.name,
        counselorId: student.counselorId,
        counselorName: student.counselorName,
        courseInterested: student.courseInterested,
        department: student.department,
        registrationDate: student.registrationDate,
        registrationTime: student.registrationTime
      })
    }

    return res.status(201).json({
      success: true,
      message: 'Thank you for registering. Your application has been received.',
      student: {
        id: student._id,
        registrationNumber: student.registrationNumber,
        name: student.name,
        counselorId: student.counselorId,
        counselorName: student.counselorName,
        courseInterested: student.courseInterested,
        department: student.department,
        registrationDate: student.registrationDate,
        registrationTime: student.registrationTime
      }
    })
  } catch (err) {
    console.error('Error submitting student registration:', err)
    return res.status(500).json({ 
      success: false, 
      message: 'Failed to process registration', 
      error: err.message 
    })
  }
})

// REAL-TIME ADMIN DASHBOARD STATS
router.get('/stats', async (req, res) => {
  try {
    const today = new Date().toISOString().split('T')[0]

    const [
      totalStudents,
      todayRegistrations,
      pendingVerification,
      approvedAdmissions,
      rejectedAdmissions,
      totalCounselors,
      documentsPending,
      deptAggregation
    ] = await Promise.all([
      StudentRegistration.countDocuments({}),
      StudentRegistration.countDocuments({ registrationDate: today }),
      StudentRegistration.countDocuments({ verificationStatus: 'Pending' }),
      StudentRegistration.countDocuments({ admissionStatus: 'Approved' }),
      StudentRegistration.countDocuments({ admissionStatus: 'Rejected' }),
      Counselor.countDocuments({ status: 'Active' }),
      StudentRegistration.countDocuments({ verificationStatus: 'Missing' }),
      StudentRegistration.aggregate([
        { $group: { _id: '$department', count: { $sum: 1 } } }
      ])
    ])

    const departmentStats = deptAggregation.reduce((acc, curr) => {
      acc[curr._id] = curr.count
      return acc
    }, {})

    return res.json({
      success: true,
      stats: {
        todayRegistrations,
        totalStudents,
        pendingVerification,
        approvedAdmissions,
        rejectedAdmissions,
        totalCounselors,
        documentsPending,
        departmentStats
      }
    })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to fetch dashboard stats', error: err.message })
  }
})

// LIST Students with search, status filters, and role-based counselor filter
router.get('/', async (req, res) => {
  try {
    const { counselorId, status, search, department, course } = req.query
    let query = {}

    if (counselorId) {
      query.counselorId = String(counselorId).toUpperCase().trim()
    }
    if (status) {
      query.admissionStatus = status
    }
    if (department) {
      query.department = department
    }
    if (course) {
      query.courseInterested = course
    }
    if (search) {
      const regex = new RegExp(search, 'i')
      query.$or = [
        { name: regex },
        { registrationNumber: regex },
        { mobile: regex },
        { email: regex },
        { counselorName: regex }
      ]
    }

    const students = await StudentRegistration.find(query).sort({ createdAt: -1 })
    return res.json({ success: true, count: students.length, students })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to list student registrations', error: err.message })
  }
})

// GET Single Student Detail
router.get('/:id', async (req, res) => {
  try {
    const student = await StudentRegistration.findById(req.params.id)
    if (!student) return res.status(404).json({ message: 'Student registration not found' })
    return res.json({ success: true, student })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to fetch student details', error: err.message })
  }
})

// UPDATE Verification Status (Admin / Counselor)
router.put('/:id/verify-docs', async (req, res) => {
  try {
    const { verificationStatus, remarks } = req.body
    const student = await StudentRegistration.findByIdAndUpdate(
      req.params.id,
      { verificationStatus, remarks },
      { new: true }
    )

    const io = req.app.get('io')
    if (io) {
      io.emit('status_updated', { studentId: student._id, type: 'verification', status: verificationStatus })
    }

    return res.json({ success: true, student })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to update verification status', error: err.message })
  }
})

// UPDATE Admission Status (Approve / Reject by Admin)
router.put('/:id/admission-status', async (req, res) => {
  try {
    const { admissionStatus, remarks, approvedBy } = req.body
    const student = await StudentRegistration.findByIdAndUpdate(
      req.params.id,
      { admissionStatus, remarks, approvedBy: approvedBy || 'Admin' },
      { new: true }
    )

    const io = req.app.get('io')
    if (io) {
      io.emit('status_updated', { studentId: student._id, type: 'admission', status: admissionStatus })
    }

    return res.json({ success: true, student })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to update admission status', error: err.message })
  }
})

// DELETE Student
router.delete('/:id', async (req, res) => {
  try {
    await StudentRegistration.findByIdAndDelete(req.params.id)
    return res.json({ success: true, message: 'Student record deleted' })
  } catch (err) {
    return res.status(500).json({ message: 'Failed to delete student', error: err.message })
  }
})

module.exports = router
