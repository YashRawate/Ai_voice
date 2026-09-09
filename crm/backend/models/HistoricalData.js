const mongoose = require('mongoose')

const historicalDataSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  sessionYear: { type: String, required: true }, // e.g., '2023-2024', '2024-2025'
  totalApplications: { type: Number, required: true },
  totalEnrolled: { type: Number, required: true },
  conversionRate: { type: Number, default: 0 },
  departmentBreakdown: [{
    department: { type: String },
    applications: { type: Number },
    enrolled: { type: Number }
  }],
  leadSourceBreakdown: [{
    source: { type: String },
    count: { type: Number },
    enrolled: { type: Number }
  }],
  notes: { type: String, default: '' }
}, { timestamps: true })

module.exports = mongoose.model('HistoricalData', historicalDataSchema)
