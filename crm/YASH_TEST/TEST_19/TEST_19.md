# TEST_19

- **Session ID:** console
- **Started:** 2026-09-10 11:01:15

### Conversation & Events

- `[  0.003s]` 🔄 **Session init** — reason=`livekit_agent_entrypoint`
- `[ 12.104s]` 🤖 **Priya replied** (stage=GENERAL): "Hello! This is Priya from Aditya University, calling about your admission enquiry. Is this a good time?"
- `[ 19.008s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Hello"
- `[ 24.311s]` 🤖 **Priya replied** (stage=GENERAL): "Yes, I'm here! May I know your name, please?"
  - facts: `{'_name_asked': True}`
- `[ 32.035s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Hello"
- `[ 36.520s]` 🤖 **Priya replied** (stage=GENERAL): "Yes, I'm here! May I know your name, please?"
  - facts: `{'_name_asked': True}`
- `[ 39.689s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "My name is Yash"
- `[ 45.817s]` 🤖 **Priya replied** (stage=GENERAL): "Nice to meet you, Yash! Which program or branch are you interested in at Aditya University?"
  - facts: `{'_name_asked': True, 'student_name': 'Yash', 'name': 'Yash'}`
- `[ 49.993s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "I am interested for B.Tech Computer Science"
- `[ 58.419s]` 🤖 **Priya replied** (stage=GENERAL): "B.Tech CSE offers specialized tracks in AI & ML, Data Science, and industry programs with SAP, Google Cloud, and Microsoft."
  - facts: `{'_name_asked': True, 'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE'}`
- `[ 62.545s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Can you please tell me about the college fee?"
- `[ 75.109s]` 🤖 **Priya replied** (stage=GENERAL): "One moment, checking tuition... B.Tech CSE fees are ₹2,75,000 per year, plus a one-time ₹15,000 admission fee. Do you want details on scholarships too, Yash?"
  - facts: `{'_name_asked': True, 'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE'}`
- `[ 79.778s]` 🎤 **Caller said** (en-IN, conf=None, snr=None): "Yes, can you please tell me the details?"
- `[ 85.657s]` 🤖 **Priya replied** (stage=GENERAL): "Looking that up... Yash, we offer up to 50% merit"
  - facts: `{'_name_asked': True, 'student_name': 'Yash', 'name': 'Yash', 'program_of_interest': 'B.Tech CSE', 'program': 'B.Tech CSE', 'specialization': 'CSE'}`

### Summary — TEST_19

| Metric | Value |
|---|---|
| Duration | 87.683s |
| Disposition | completed |
| Turns | 13 |
| Interruptions | 0 |
| Session re-inits | 1 (✅ OK) |
| Language switches | 0 |
| Reconnects | 0 |
| Errors | 0 |
| Notes | LiveKit room session closed |
| File Path | C:\Users\yashr\OneDrive\Desktop\Ai_voice-main\crm\YASH_TEST\TEST_19.md |

