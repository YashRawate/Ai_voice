const mongoose = require('mongoose')

const workflowRuleSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  name: { type: String, required: true, trim: true },
  triggerEvent: {
    type: String,
    enum: ['lead_created', 'application_submitted', 'document_uploaded', 'payment_pending', 'lead_unassigned', 'application_approved'],
    required: true
  },
  conditions: {
    status: { type: String, default: '' },
    course: { type: String, default: '' },
    source: { type: String, default: '' },
    minScore: { type: Number, default: 0 }
  },
  actions: [{
    actionType: {
      type: String,
      enum: ['send_whatsapp', 'send_email', 'send_sms', 'assign_counselor', 'add_tag', 'trigger_lms', 'create_task'],
      required: true
    },
    config: { type: Object, default: {} }
  }],
  isActive: { type: Boolean, default: true },
  executionCount: { type: Number, default: 0 },
  lastTriggeredAt: { type: Date, default: null }
}, { timestamps: true })

module.exports = mongoose.model('WorkflowRule', workflowRuleSchema)
