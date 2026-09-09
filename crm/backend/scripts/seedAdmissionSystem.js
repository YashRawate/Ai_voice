require('dotenv').config()
const connectDB = require('../config/db')
const Counselor = require('../models/Counselor')
const Organization = require('../models/Organization')
const College = require('../models/College')
const QRCodeCampaign = require('../models/QRCodeCampaign')
const StudentRegistration = require('../models/StudentRegistration')

async function seed() {
  await connectDB()
  console.log('Seeding Admission System data...')

  let org = await Organization.findOne({})
  if (!org) {
    org = await Organization.create({ name: 'Aditya Group of Institutions', slug: 'aditya' })
  }

  let college = await College.findOne({})
  if (!college) {
    college = await College.create({ orgId: org._id, name: 'Aditya University Surampalem', city: 'Surampalem', code: 'AU' })
  }

  // Seed Counselors AEC001, AEC002, AEC003
  const counselorsData = [
    { counselorId: 'AEC001', name: 'Rajesh Kumar', mobile: '9848012345', email: 'rajesh.aec@aditya.ac.in', department: 'Admissions & Engineering', campus: 'Aditya University Main Campus' },
    { counselorId: 'AEC002', name: 'Priya Sharma', mobile: '9848054321', email: 'priya.aec@aditya.ac.in', department: 'Management & Pharmacy', campus: 'Aditya University Surampalem' },
    { counselorId: 'AEC003', name: 'Venkatesh Rao', mobile: '9848099887', email: 'venkatesh.aec@aditya.ac.in', department: 'Polytechnic & Diploma', campus: 'Aditya Campus Kakinada' },
  ]

  for (const c of counselorsData) {
    const existing = await Counselor.findOne({ counselorId: c.counselorId })
    if (!existing) {
      await Counselor.create({
        orgId: org._id,
        branchId: college._id,
        ...c,
        status: 'Active'
      })
      console.log(`Created Counselor: ${c.counselorId} (${c.name})`)
    }
  }

  // Seed QR Campaign
  const qrData = {
    orgId: org._id,
    branchId: college._id,
    title: 'Aditya University Admissions 2026 QR Portal',
    code: 'AU-2026-QR',
    collegeName: 'Aditya University',
    department: 'Engineering & Technology',
    campus: 'Main Campus Surampalem',
    campaignName: 'Direct Campus Scan 2026',
    targetUrl: 'http://localhost:5173/student-register?qr=AU-2026-QR'
  }

  const existingQr = await QRCodeCampaign.findOne({ code: qrData.code })
  if (!existingQr) {
    await QRCodeCampaign.create(qrData)
    console.log(`Created QR Code: ${qrData.code}`)
  }

  // Seed 10 Realistic Student Admission Registrations
  const today = new Date().toISOString().split('T')[0]
  const sampleStudents = [
    {
      registrationNumber: 'AEC2026-104821',
      counselorId: 'AEC001',
      counselorName: 'Rajesh Kumar',
      registrationDate: today,
      registrationTime: '09:30:15',
      name: 'Naveen Kumar Varma',
      fatherName: 'Srinivasa Varma',
      motherName: 'Lakshmi Varma',
      dob: '2005-04-12',
      gender: 'Male',
      category: 'General',
      aadhaarNumber: '784512963012',
      mobile: '9848011223',
      email: 'naveen.varma@gmail.com',
      address: 'Plot 42, Main Road, Danavaipeta',
      city: 'Rajahmundry',
      district: 'East Godavari',
      state: 'Andhra Pradesh',
      pincode: '533103',
      sscSchool: 'St. Joseph English Medium High School',
      sscPercentage: 94.2,
      interCollege: 'Aditya Junior College Rajahmundry',
      interPercentage: 96.5,
      entranceExam: 'EAMCET',
      rank: 8420,
      yearOfPassing: 2026,
      courseInterested: 'B.Tech Computer Science (CSE)',
      department: 'Computer Science & Engineering',
      preferredCampus: 'Aditya University Surampalem',
      hostelRequired: 'Yes',
      transportRequired: 'No',
      verificationStatus: 'Verified',
      admissionStatus: 'Approved'
    },
    {
      registrationNumber: 'AEC2026-104822',
      counselorId: 'AEC001',
      counselorName: 'Rajesh Kumar',
      registrationDate: today,
      registrationTime: '10:15:42',
      name: 'Kavya Sree Pendyala',
      fatherName: 'Rambabu Pendyala',
      motherName: 'Sunitha Pendyala',
      dob: '2005-08-25',
      gender: 'Female',
      category: 'OBC',
      aadhaarNumber: '895623147896',
      mobile: '9848022334',
      email: 'kavya.pendyala@gmail.com',
      address: 'D.No 12-4-5, Temple Street',
      city: 'Kakinada',
      district: 'Kakinada',
      state: 'Andhra Pradesh',
      pincode: '533001',
      sscSchool: 'Sri Chaitanya Techno School',
      sscPercentage: 98.0,
      interCollege: 'Aditya Junior College Kakinada',
      interPercentage: 97.2,
      entranceExam: 'EAMCET',
      rank: 4210,
      yearOfPassing: 2026,
      courseInterested: 'B.Tech Artificial Intelligence & Data Science',
      department: 'Computer Science & Engineering',
      preferredCampus: 'Aditya University Surampalem',
      hostelRequired: 'No',
      transportRequired: 'Yes',
      verificationStatus: 'Verified',
      admissionStatus: 'Approved'
    },
    {
      registrationNumber: 'AEC2026-104823',
      counselorId: 'AEC002',
      counselorName: 'Priya Sharma',
      registrationDate: today,
      registrationTime: '11:05:20',
      name: 'Sai Teja Reddy',
      fatherName: 'Venkata Reddy',
      motherName: 'Padma Reddy',
      dob: '2005-11-04',
      gender: 'Male',
      category: 'General',
      aadhaarNumber: '451278963254',
      mobile: '9848033445',
      email: 'saiteja.reddy@gmail.com',
      address: 'House 8, Subhash Nagar',
      city: 'Eluru',
      district: 'West Godavari',
      state: 'Andhra Pradesh',
      pincode: '534001',
      sscSchool: 'Narayana High School',
      sscPercentage: 88.4,
      interCollege: 'Narayana Junior College',
      interPercentage: 89.0,
      entranceExam: 'EAMCET',
      rank: 18450,
      yearOfPassing: 2026,
      courseInterested: 'MBA (Master of Business Administration)',
      department: 'Management Studies',
      preferredCampus: 'Aditya University Surampalem',
      hostelRequired: 'Yes',
      transportRequired: 'No',
      verificationStatus: 'Pending',
      admissionStatus: 'Pending'
    },
    {
      registrationNumber: 'AEC2026-104824',
      counselorId: 'AEC002',
      counselorName: 'Priya Sharma',
      registrationDate: today,
      registrationTime: '11:45:10',
      name: 'Bhavana Chodisetty',
      fatherName: 'Satyanarayana Chodisetty',
      motherName: 'Rama Devi',
      dob: '2005-02-18',
      gender: 'Female',
      category: 'OBC',
      aadhaarNumber: '963258741025',
      mobile: '9848044556',
      email: 'bhavana.chodisetty@gmail.com',
      address: 'Near Clock Tower',
      city: 'Amalapuram',
      district: 'Konaseema',
      state: 'Andhra Pradesh',
      pincode: '533201',
      sscSchool: 'Zilla Parishad High School',
      sscPercentage: 91.5,
      interCollege: 'Aditya Junior College Amalapuram',
      interPercentage: 93.8,
      entranceExam: 'EAMCET',
      rank: 12100,
      yearOfPassing: 2026,
      courseInterested: 'B.Tech Electronics & Communication (ECE)',
      department: 'Electronics & Communication',
      preferredCampus: 'Aditya University Surampalem',
      hostelRequired: 'Yes',
      transportRequired: 'No',
      verificationStatus: 'Pending',
      admissionStatus: 'Pending'
    },
    {
      registrationNumber: 'AEC2026-104825',
      counselorId: 'AEC003',
      counselorName: 'Venkatesh Rao',
      registrationDate: today,
      registrationTime: '12:20:30',
      name: 'Dinesh Kumar Ganti',
      fatherName: 'Subrahmanyam Ganti',
      motherName: 'Sujatha Ganti',
      dob: '2006-01-30',
      gender: 'Male',
      category: 'SC',
      aadhaarNumber: '124578963014',
      mobile: '9848055667',
      email: 'dinesh.ganti@gmail.com',
      address: 'Main Bazaar Road',
      city: 'Tuni',
      district: 'Kakinada',
      state: 'Andhra Pradesh',
      pincode: '533401',
      sscSchool: 'Government High School Tuni',
      sscPercentage: 85.0,
      interCollege: 'Government Junior College',
      interPercentage: 86.5,
      entranceExam: 'POLYCET',
      rank: 3200,
      yearOfPassing: 2026,
      courseInterested: 'Diploma / Polytechnic',
      department: 'Mechanical Engineering',
      preferredCampus: 'Aditya Campus Kakinada',
      hostelRequired: 'No',
      transportRequired: 'Yes',
      verificationStatus: 'Verified',
      admissionStatus: 'Approved'
    }
  ]

  for (const s of sampleStudents) {
    const existing = await StudentRegistration.findOne({ registrationNumber: s.registrationNumber })
    if (!existing) {
      await StudentRegistration.create({
        orgId: org._id,
        branchId: college._id,
        ...s
      })
      console.log(`Created Student: ${s.registrationNumber} (${s.name})`)
    }
  }

  console.log('Seeding finished successfully!')
  process.exit(0)
}

seed().catch(err => {
  console.error(err)
  process.exit(1)
})
