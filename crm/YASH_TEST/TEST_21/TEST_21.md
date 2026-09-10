# TEST_21

- **Session ID:** console
- **Started:** 2026-09-10 11:02:52

### Conversation & Events

- `[  0.003s]` 🔄 **Session init** — reason=`livekit_agent_entrypoint`
- `[ 10.906s]` 🤖 **Priya replied** (stage=GENERAL): "Hello! This is Priya from Aditya University, calling about your admission enquiry. Is this a good time?"
- `[ 14.006s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Yes, it is a good time."
- `[ 16.907s]` 🤖 **Priya replied** (stage=GENERAL): "May I know your name, please?"
- `[ 19.206s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "My name is Yash"
- `[ 22.104s]` 🤖 **Priya replied** (stage=GENERAL): "Nice to meet you, Yash! Which program"
  - facts: `{'student_name': 'Yash', 'name': 'Yash'}`
- `[ 22.121s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Hmm"
- `[ 27.811s]` 🤖 **Priya replied** (stage=GENERAL): "Yash, which program or branch are you interested in at Aditya University?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash'}`
- `[ 32.749s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "I am interested for computer science."
- `[ 41.709s]` 🤖 **Priya replied** (stage=GENERAL): "B.Tech CSE offers specialized tracks in AI & ML, Data Science, and industry programs with SAP, Google Cloud, and Microsoft."
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE'}`
- `[ 47.116s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Okay, can you please tell me about the hostel fee?"
- `[ 58.210s]` 🤖 **Priya replied** (stage=GENERAL): "We provide AC and Non-AC hostel options with attached bathrooms and multi-cuisine meals. Would you like me to send the direct admission link to reserve your seat and hostel room?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes'}`
- `[ 60.999s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Yes, can you please send a link?"
- `[ 70.812s]` 🤖 **Priya replied** (stage=GENERAL): "Let me get that information... Great, Yash! I’m sending the direct application link to your WhatsApp now to reserve your seat. Anything else you’d like to know?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested'}`
- `[ 79.423s]` 🌐 **Language switch** en-IN → hi-IN (conf=None)
- `[ 79.460s]` 🎤 **Caller said** (hi-IN, conf=None, snr=None): "क्या आप मुझे बता सकते हो कि हॉस्टल फी और कॉलेज फी दोनों मिला के एक साल में कितना देना होगा?"
- `[ 89.310s]` 🤖 **Priya replied** (stage=GENERAL): "Campus mein AC aur Non-AC hostel facilities meals ke saath available hain: Non-AC 30 thousand rupees aur AC 45 thousand rupees per semester."
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested'}`
- `[ 93.598s]` 🎤 **Caller said** (hi-IN, conf=None, snr=None): "और एक साल में कितना देना होगा?"
- `[105.311s]` 🤖 **Priya replied** (stage=GENERAL): "जी, जानकारी देख रही हूँ... Yash ji, AC hostel ₹1,30,000 per year, Non-AC ₹1,15,000 per year. Tuition fees alag hain, aapko program batayein?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested'}`
- `[111.876s]` 🎤 **Caller said** (hi-IN, conf=None, snr=None): "अच्छा।"
- `[112.449s]` 🎤 **Caller said** (hi-IN, conf=None, snr=None): "आप कॉलेज फी के बारे में बता सकते हो?"
- `[122.591s]` 🌐 **Language switch** hi-IN → en-IN (conf=None)
- `[122.645s]` 🤖 **Priya replied** (stage=GENERAL): "एक मिनट रुकिए, चेक कर रही हूँ... Yash ji, B.Tech CSE fees ₹2,75,000 per year; core branches ₹1,00,000 to ₹1,35,000"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested'}`
- `[122.701s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "per year."
- `[123.846s]` 🌐 **Language switch** en-IN → hi-IN (conf=None)
- `[128.110s]` 🤖 **Priya replied** (stage=GENERAL): "जी हाँ, Yash ji, ये फीस सालाना है। आपके 12वीं के मार्क्स क्या हैं?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested'}`
- `[131.757s]` 🌐 **Language switch** hi-IN → en-IN (conf=None)
- `[131.848s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "79%"
- `[133.357s]` 🌐 **Language switch** en-IN → hi-IN (conf=None)
- `[136.937s]` 🤖 **Priya replied** (stage=GENERAL): "बहुत बढ़िया, Yash ji! आपकी स्कोर 79% है, जो हमारे"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested', 'class_12_score': '79.0%', 'score': '79%'}`
- `[136.982s]` 🎤 **Caller said** (hi-IN, conf=None, snr=None): "बहुत बढ़िया यश जी।"
- `[142.311s]` 🤖 **Priya replied** (stage=GENERAL): "धन्यवाद, Yash जी! कौन सा प्रोग्राम या ब्रांच में रुचि रखते हैं आप?"
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested', 'class_12_score': '79.0%', 'score': '79%'}`
- `[146.582s]` 🌐 **Language switch** hi-IN → en-IN (conf=None)
- `[146.679s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Okay, bye bye."
- `[152.383s]` 🤖 **Priya replied** (stage=GENERAL): "Thank you for reaching out to Aditya University! Wishing you all the best for your admissions."
  - facts: `{'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE', 'hostel_interest': 'Yes', 'engagement_choice': 'application_link', 'call_outcome': 'interested', 'class_12_score': '79.0%', 'score': '79%'}`
- `[152.423s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Wishing you all the best for your future."
- `[164.855s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "University calling about your admission inquiry. Yes, it's a good time. Yes, it is a good time."

### Summary — TEST_21

| Metric | Value |
|---|---|
| Duration | 164.903s |
| Disposition | completed |
| Turns | 30 |
| Interruptions | 0 |
| Session re-inits | 1 (✅ OK) |
| Language switches | 6 |
| Reconnects | 0 |
| Errors | 0 |
| Notes | LiveKit room session closed |
| File Path | C:\Users\yashr\OneDrive\Desktop\Ai_voice-main\crm\YASH_TEST\TEST_21.md |

