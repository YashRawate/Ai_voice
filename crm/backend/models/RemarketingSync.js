const mongoose = require('mongoose')

const remarketingSyncSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  platform: { type: String, enum: ['facebook', 'google_ads', 'all'], required: true },
  audienceName: { type: String, required: true },
  segmentFilter: {
    status: { type: String, default: '' },
    minLeadScore: { type: Number, default: 0 },
    unsubmittedDays: { type: Number, default: 0 },
    department: { type: String, default: '' }
  },
  autoSync: { type: Boolean, default: true },
  syncFrequencyHours: { type: Number, default: 24 },
  lastSyncedAt: { type: Date, default: null },
  matchedAudienceCount: { type: Number, default: 0 },
  status: { type: String, enum: ['active', 'paused', 'syncing', 'error'], default: 'active' },
  lastError: { type: String, default: '' }
}, { timestamps: true })

module.exports = mongoose.model('RemarketingSync', remarketingSyncSchema)
