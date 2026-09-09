const mongoose = require('mongoose')

const paymentTransactionSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  studentRegistrationId: { type: mongoose.Schema.Types.ObjectId, ref: 'StudentRegistration', default: null },
  registrationNumber: { type: String, required: true, index: true },
  studentName: { type: String, required: true },
  feeType: { type: String, enum: ['Application Fee', 'Seat Reservation', 'Tuition Fee', 'Hostel Fee', 'Other'], default: 'Application Fee' },
  amount: { type: Number, required: true },
  paymentStatus: { type: String, enum: ['Pending', 'Completed', 'Failed', 'Refunded'], default: 'Pending', index: true },
  paymentLink: { type: String, default: '' },
  transactionId: { type: String, default: '' },
  paymentMethod: { type: String, default: 'UPI/Online' },
  paidAt: { type: Date, default: null },
  offerLetterIssued: { type: Boolean, default: false },
  offerLetterUrl: { type: String, default: '' }
}, { timestamps: true })

module.exports = mongoose.model('PaymentTransaction', paymentTransactionSchema)
