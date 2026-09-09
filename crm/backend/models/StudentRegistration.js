const mongoose = require('mongoose')

const studentRegistrationSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  branchId: { type: mongoose.Schema.Types.ObjectId, ref: 'College', required: true, index: true },

  registrationNumber: { type: String, required: true, unique: true, index: true }, // e.g. AEC2026-000125

  // Mandatory Admission Counselor Linkage
  counselorId: { type: String, required: true, uppercase: true, trim: true, index: true },
  counselorName: { type: String, required: true },
  registrationDate: { type: String, required: true }, // YYYY-MM-DD
  registrationTime: { type: String, required: true }, // HH:mm:ss

  // Personal Information
  name: { type: String, required: true, trim: true },
  fatherName: { type: String, required: true, trim: true },
  motherName: { type: String, required: true, trim: true },
  dob: { type: String, required: true },
  gender: { type: String, enum: ['Male', 'Female', 'Other'], required: true },
  category: { type: String, enum: ['General', 'OBC', 'SC', 'ST', 'EWS', 'Other'], default: 'General' },
  aadhaarNumber: { type: String, required: true, index: true, trim: true },
  bloodGroup: { type: String, default: 'O+' },

  // Contact Details
  mobile: { type: String, required: true, index: true, trim: true },
  altMobile: { type: String, default: '' },
  email: { type: String, required: true, index: true, lowercase: true, trim: true },
  address: { type: String, required: true },
  city: { type: String, required: true, index: true },
  district: { type: String, required: true, index: true },
  state: { type: String, required: true, index: true },
  pincode: { type: String, required: true },

  // Academic Information
  sscSchool: { type: String, required: true },
  sscPercentage: { type: Number, required: true },
  interCollege: { type: String, required: true },
  interPercentage: { type: Number, required: true },
  diplomaDetails: { type: String, default: '' },
  entranceExam: { type: String, enum: ['EAMCET', 'JEE', 'ECET', 'POLYCET', 'Others', 'None'], default: 'EAMCET' },
  rank: { type: Number, default: 0 },
  yearOfPassing: { type: Number, required: true },

  // Admission Details
  courseInterested: { type: String, required: true, index: true },
  department: { type: String, required: true, index: true },
  preferredCampus: { type: String, required: true },
  hostelRequired: { type: String, enum: ['Yes', 'No'], default: 'No' },
  transportRequired: { type: String, enum: ['Yes', 'No'], default: 'No' },

  // Uploaded Documents Summary / Ref
  documents: {
    photoUrl: { type: String, default: '' },
    aadhaarUrl: { type: String, default: '' },
    sscMemoUrl: { type: String, default: '' },
    interMemoUrl: { type: String, default: '' },
    tcUrl: { type: String, default: '' },
    casteCertUrl: { type: String, default: '' },
    incomeCertUrl: { type: String, default: '' },
    migrationCertUrl: { type: String, default: '' },
  },

  // Verification & Admission Status
  verificationStatus: { 
    type: String, 
    enum: ['Pending', 'Verified', 'Rejected', 'Missing'], 
    default: 'Pending', 
    index: true 
  },
  admissionStatus: { 
    type: String, 
    enum: ['Pending', 'Approved', 'Rejected'], 
    default: 'Pending', 
    index: true 
  },
  remarks: { type: String, default: '' },
  forwardedToAdminAt: { type: Date, default: Date.now },
  approvedBy: { type: String, default: null },

  // Campaign / QR linkage
  qrCampaignId: { type: mongoose.Schema.Types.ObjectId, ref: 'QRCodeCampaign', default: null }

}, { timestamps: true })

// Duplicate index check helper across org
studentRegistrationSchema.index({ orgId: 1, mobile: 1 }, { unique: true })
studentRegistrationSchema.index({ orgId: 1, email: 1 }, { unique: true })
studentRegistrationSchema.index({ orgId: 1, aadhaarNumber: 1 }, { unique: true })

module.exports = mongoose.model('StudentRegistration', studentRegistrationSchema)
