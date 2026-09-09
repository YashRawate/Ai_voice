const mongoose = require('mongoose')

const qrCodeCampaignSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  branchId: { type: mongoose.Schema.Types.ObjectId, ref: 'College', required: true, index: true },
  title: { type: String, required: true },
  code: { type: String, required: true, unique: true, uppercase: true, trim: true }, // e.g. QR-ADMISSION-2026
  collegeName: { type: String, default: 'Aditya University' },
  department: { type: String, default: 'Engineering' },
  campus: { type: String, default: 'Main Campus' },
  campaignName: { type: String, default: 'General Admissions 2026' },
  targetUrl: { type: String, required: true },

  // Analytics
  scansCount: { type: Number, default: 0 },
  successfulRegistrations: { type: Number, default: 0 },
  status: { type: String, enum: ['Active', 'Paused', 'Archived'], default: 'Active' },
}, { timestamps: true })

module.exports = mongoose.model('QRCodeCampaign', qrCodeCampaignSchema)
