// ---------------------------------------------------------------------------
// Priya-specific Twilio service — only used for outbound calls triggered
// from the Admin dashboard.  The existing telephony.js handles campaign
// calls; this file handles single-student Priya sessions.
// ---------------------------------------------------------------------------
const twilio = require('twilio')

function getClient() {
  const sid   = process.env.TWILIO_ACCOUNT_SID
  const token = process.env.TWILIO_AUTH_TOKEN
  if (!sid || !token || sid.startsWith('AC__')) {
    throw new Error('Twilio credentials not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN)')
  }
  return twilio(sid, token)
}

/**
 * Initiate an outbound call to `to` for the given Priya session.
 * Twilio will POST to  /webhook/call-start?session_id=<id>  when the call
 * connects, and POST to /webhook/call-status?session_id=<id> for status updates.
 */
async function makeOutboundCall({ to, sessionId }) {
  const publicUrl = process.env.DIRECT_PUBLIC_URL || process.env.PUBLIC_BACKEND_URL || process.env.SERVER_URL

  if (!publicUrl) throw new Error('SERVER_URL / DIRECT_PUBLIC_URL not set in .env')

  // Route directly to Priya direct audio pipeline if DIRECT_PUBLIC_URL is configured
  const webhookUrl = process.env.DIRECT_PUBLIC_URL
    ? `${process.env.DIRECT_PUBLIC_URL.replace(/\/$/, '')}/twiml?session_id=${sessionId}`
    : `${publicUrl}/webhook/call-start?session_id=${sessionId}`

  console.log('[Twilio] >>> Calling', to, 'with webhook:', webhookUrl)

  const client = getClient()
  const callPayload = {
    to,
    from: process.env.TWILIO_PHONE_NUMBER,
    url: webhookUrl,
  }

  // Only add statusCallback if public backend is available
  if (process.env.PUBLIC_BACKEND_URL && !process.env.PUBLIC_BACKEND_URL.includes('localhost')) {
    callPayload.statusCallback = `${process.env.PUBLIC_BACKEND_URL}/webhook/call-status?session_id=${sessionId}`
    callPayload.statusCallbackMethod = 'POST'
    callPayload.statusCallbackEvent = ['completed', 'failed', 'busy', 'no-answer']
  }

  const call = await client.calls.create(callPayload)


  console.log('[Twilio] Call created:', call.sid, '| to:', to)
  return call
}

module.exports = { makeOutboundCall }
