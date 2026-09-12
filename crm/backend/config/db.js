const mongoose = require('mongoose')

async function connectDB() {
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/admitai'
  try {
    await mongoose.connect(uri, { serverSelectionTimeoutMS: 2000 })
    console.log(`MongoDB connected: ${mongoose.connection.host}`)
  } catch (err) {
    console.warn(`Local MongoDB unavailable (${err.message}). Starting in-memory development database...`)
    try {
      const { MongoMemoryServer } = require('mongodb-memory-server')
      const mongod = await MongoMemoryServer.create()
      const memUri = mongod.getUri()
      await mongoose.connect(memUri)
      console.log(`✅ Connected to in-memory MongoDB: ${memUri}`)
    } catch (fallbackErr) {
      console.error('MongoDB fallback connection error:', fallbackErr.message)
      process.exit(1)
    }
  }
}

module.exports = connectDB
