const mongoose = require('mongoose')

const supportTicketSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  ticketNumber: { type: String, required: true, unique: true },
  submittedBy: { type: String, required: true },
  email: { type: String, required: true },
  category: { type: String, enum: ['Admissions', 'Payment Issue', 'LMS Access', 'Counselor Dispute', 'System Bug', 'General Inquiry'], default: 'General Inquiry' },
  priority: { type: String, enum: ['Low', 'Medium', 'High', 'Urgent'], default: 'Medium' },
  subject: { type: String, required: true },
  description: { type: String, required: true },
  status: { type: String, enum: ['Open', 'In Progress', 'Resolved', 'Closed'], default: 'Open', index: true },
  assignedTo: { type: String, default: 'Unassigned' },
  resolutionNotes: { type: String, default: '' },
  resolvedAt: { type: Date, default: null }
}, { timestamps: true })

module.exports = mongoose.model('SupportTicket', supportTicketSchema)
