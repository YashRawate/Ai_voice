const mongoose = require('mongoose')

const counselorSchema = new mongoose.Schema({
  orgId: { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true, index: true },
  branchId: { type: mongoose.Schema.Types.ObjectId, ref: 'College', required: true, index: true },
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', default: null },

  counselorId: { 
    type: String, 
    required: true, 
    unique: true, 
    uppercase: true, 
    trim: true, 
    index: true 
  }, // e.g. AEC001, AEC002
  
  name: { type: String, required: true, trim: true },
  mobile: { type: String, required: true, trim: true },
  email: { type: String, required: true, lowercase: true, trim: true },
  department: { type: String, default: 'Admissions' },
  campus: { type: String, default: 'Main Campus' },
  status: { type: String, enum: ['Active', 'Disabled'], default: 'Active' },
}, { timestamps: true })

module.exports = mongoose.model('Counselor', counselorSchema)
