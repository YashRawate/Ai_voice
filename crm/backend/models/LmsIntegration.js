const mongoose = require('mongoose')

const lmsIntegrationSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  lmsType: { type: String, enum: ['Moodle', 'Canvas', 'Blackboard', 'CustomWebhook'], default: 'Canvas' },
  endpointUrl: { type: String, default: '' },
  apiKey: { type: String, default: '' },
  autoSyncOnEnrollment: { type: Boolean, default: true },
  totalSyncedStudents: { type: Number, default: 0 },
  lastSyncAt: { type: Date, default: null },
  syncLogs: [{
    studentRegistrationId: { type: mongoose.Schema.Types.ObjectId, ref: 'StudentRegistration' },
    registrationNumber: { type: String },
    status: { type: String, enum: ['Success', 'Failed'] },
    responseMessage: { type: String },
    syncedAt: { type: Date, default: Date.now }
  }]
}, { timestamps: true })

module.exports = mongoose.model('LmsIntegration', lmsIntegrationSchema)
