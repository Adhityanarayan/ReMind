# Auto-Learning Feature Guide

## Overview

The ReMind V2 web app now includes **automatic learning** - the system can learn new people without any pre-existing database information. It listens to conversations, extracts person information from speech, collects face samples automatically, and enrolls new people on the fly.

---

## How It Works

### The Auto-Learning Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  1. Unknown Face Detected                                     │
│     • Camera detects face not in database                    │
│     • System shows "Unknown - Listening..." label            │
│     • Starts collecting face samples automatically           │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  2. Speech Recognition Active                                 │
│     • Whisper AI transcribes conversation in real-time       │
│     • Transcript appears at bottom of screen                 │
│     • Text saved to transcript buffer                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  3. Metadata Extraction                                       │
│     • System analyzes conversation for person info           │
│     • Looks for patterns like "my name is..." or "I'm..."   │
│     • Extracts: name, relationship                           │
│     • Requires 60% confidence minimum                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  4. Learning Status Displayed                                 │
│     • UI shows "Learning: [Name]" card                       │
│     • Progress bar shows face samples (X/10)                 │
│     • Video shows "Learning: [Name]" label                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  5. Ready to Enroll                                           │
│     • 10+ face samples collected                             │
│     • Name extracted from speech                             │
│     • "Enroll [Name]" button appears                         │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  6. Auto-Enrollment                                           │
│     • User clicks "Enroll" button                            │
│     • Face encoding saved to database                        │
│     • Person now in system permanently                       │
│     • Will be recognized on future visits                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Start the Web App

```bash
cd /Users/adhitya/Development/ReMind/face_detection
python3 apps/web_app.py
```

**Options:**
```bash
# Use different Whisper model (better accuracy, slower)
python3 apps/web_app.py --whisper base

# Change port
python3 apps/web_app.py --port 8080

# Use different database
python3 apps/web_app.py --db my_remind.db
```

### 2. Open in Browser

Navigate to: `http://localhost:5001`

You'll see:
- **Left panel:** Live video feed with face detection
- **Right panel:** Person information (initially empty)
- **Bottom:** Live transcript section

### 3. Test the Auto-Learning

**Step 1:** Stand in front of camera
- Red box appears around face: "Unknown - Listening..."
- System starts collecting face samples automatically

**Step 2:** Introduce yourself clearly
- Say: "Hello, my name is Sarah Johnson. I'm the daughter."
- Or: "Hi, I'm Dr. Smith, the primary care physician."
- Or: "My name is John and I'm a friend."

**Step 3:** Watch the system learn
- Person info panel shows: "🎓 Learning New Person"
- Name and relationship detected from speech
- Progress bar shows face samples: 1/10, 2/10, etc.
- Keep looking at camera until 10/10 samples collected

**Step 4:** Enroll the person
- When 10+ samples collected, "✨ Enroll [Name]" button appears
- Click the button
- Success message: "Successfully enrolled [Name]!"

**Step 5:** Verify recognition
- Walk away from camera
- Return to view
- System should now recognize you with green box
- Name and information displayed automatically

---

## Features

### 1. Real-Time Speech Transcription

- **Technology:** OpenAI Whisper AI
- **Language:** English (configurable)
- **Accuracy:** 95%+ word accuracy
- **Display:** Live transcript at bottom of screen
- **Format:**
  ```
  [14:32:15] Sarah: Hello, my name is Sarah Johnson
  [14:32:18] Sarah: I'm the daughter
  [14:32:22] Sarah: I visit every Tuesday
  ```

### 2. Intelligent Metadata Extraction

The system automatically detects:

**Name Patterns:**
- "My name is [Name]"
- "I'm [Name]"
- "This is [Name]"
- "Call me [Name]"
- "[Name] here"

**Relationship Patterns:**
- "I'm the [relationship]"
- "I'm her/his [relationship]"
- "[Relationship] visiting"
- Common relationships: daughter, son, doctor, nurse, friend, neighbor, caregiver

**Confidence Scoring:**
- System calculates confidence (0-100%)
- Only accepts suggestions with 60%+ confidence
- Higher confidence = more certain detection

### 3. Automatic Face Sample Collection

- **Samples needed:** 10 minimum (collects up to 20)
- **Quality:** Various angles and lighting automatically
- **Storage:** Kept in memory during learning
- **Encoding:** Converted to 128-d face encoding on enrollment
- **Database:** Stored as BLOB in SQLite

### 4. Progressive UI Feedback

**Unknown face (no info yet):**
```
┌─────────────────────────────────┐
│ No Person Detected              │
│ Waiting for someone to appear..│
│ System will learn automatically │
│ when you introduce yourself     │
└─────────────────────────────────┘
```

**Learning in progress:**
```
┌──────────────────────────────────┐
│ 🎓 Learning New Person           │
│ Name detected: Sarah Johnson     │
│ Relationship: Daughter           │
│ Confidence: 85%                  │
│                                  │
│ Face samples: 7/10               │
│ ████████████░░░░░░░░ 70%        │
│                                  │
│ Collecting face samples...       │
│ Keep looking at camera           │
└──────────────────────────────────┘
```

**Ready to enroll:**
```
┌──────────────────────────────────┐
│ 🎓 Learning New Person           │
│ Name detected: Sarah Johnson     │
│ Relationship: Daughter           │
│ Confidence: 85%                  │
│                                  │
│ Face samples: 12/10              │
│ ████████████████████ 100%        │
│                                  │
│ ┌──────────────────────────────┐│
│ │  ✨ Enroll Sarah Johnson    ││
│ └──────────────────────────────┘│
└──────────────────────────────────┘
```

**Recognized person:**
```
┌──────────────────────────────────┐
│ Sarah Johnson                    │
│ Daughter                         │
│ Match: 98.5%                     │
├──────────────────────────────────┤
│ 📞 Contact Information           │
│ [contact details if available]   │
├──────────────────────────────────┤
│ 📊 Visit Statistics              │
│ Total Visits: 5                  │
│ Last seen: 2 days ago            │
├──────────────────────────────────┤
│ 💭 Recent Discussion Topics      │
│ • Medication schedule            │
│ • Doctor appointment             │
└──────────────────────────────────┘
```

---

## API Endpoints

The web app provides REST API endpoints for integration:

### GET `/api/current_person`

Get currently recognized person or learning status.

**Response (recognized):**
```json
{
  "status": "recognized",
  "person": {
    "id": 1,
    "name": "Sarah Johnson",
    "relationship": "Daughter",
    "phone": "555-1234",
    "important_info": "...",
    "match_confidence": 98.5
  },
  "encounters": {
    "total_visits": 5,
    "last_seen": "2 days ago",
    "common_topics": [...]
  }
}
```

**Response (learning):**
```json
{
  "status": "learning",
  "candidate": {
    "name": "Sarah Johnson",
    "relationship": "Daughter",
    "confidence": 0.85
  },
  "samples_collected": 12,
  "samples_needed": 10
}
```

**Response (no person):**
```json
{
  "status": "no_person"
}
```

### GET `/api/transcript`

Get recent conversation transcript.

**Response:**
```json
{
  "transcript": [
    {
      "time": "14:32:15",
      "speaker": "Sarah",
      "text": "Hello, my name is Sarah Johnson"
    },
    {
      "time": "14:32:18",
      "speaker": "Sarah",
      "text": "I'm the daughter"
    }
  ],
  "full_length": 245
}
```

### POST `/api/auto_enroll`

Trigger automatic enrollment of learning candidate.

**Request:** (no body required)

**Response (success):**
```json
{
  "success": true,
  "person_id": 1,
  "name": "Sarah Johnson",
  "message": "Successfully enrolled Sarah Johnson!"
}
```

**Response (failure):**
```json
{
  "success": false,
  "message": "Need more face samples (7/10)"
}
```

### GET `/api/learning_status`

Get current learning status.

**Response:**
```json
{
  "is_learning": true,
  "candidate": {
    "name": "Sarah Johnson",
    "relationship": "Daughter",
    "confidence": 0.85
  },
  "samples_collected": 12,
  "samples_needed": 10,
  "ready_to_enroll": true
}
```

---

## Configuration

### Whisper Model Selection

Trade-off: **Speed vs. Accuracy**

| Model  | Size   | Speed      | Accuracy | Use Case                    |
|--------|--------|------------|----------|-----------------------------|
| `tiny` | 39 MB  | Very Fast  | Good     | Real-time, limited resources|
| `base` | 74 MB  | Fast       | Better   | Balanced performance        |
| `small`| 244 MB | Moderate   | Best     | High accuracy needed        |

**Change model:**
```bash
python3 apps/web_app.py --whisper base
```

### Recognition Tolerance

Edit [apps/web_app.py](../apps/web_app.py#L70):

```python
face_recognition = FaceRecognitionManager(db_path, tolerance=0.6)
```

- **0.5** = Stricter (fewer false positives)
- **0.6** = Default (balanced)
- **0.7** = Looser (may have false positives)

### Face Sample Requirements

Edit [apps/web_app.py](../apps/web_app.py#L225):

```python
if len(unknown_face_samples) < 10:  # Change this number
```

- **Minimum 5** samples (not recommended - lower accuracy)
- **10 samples** (default - good balance)
- **15-20 samples** (better accuracy, takes longer)

### Camera Index

Edit [apps/web_app.py](../apps/web_app.py#L93):

```python
camera = cv2.VideoCapture(1)  # Change index
```

- **0** = Built-in laptop camera
- **1** = First external camera
- **2+** = Additional cameras

---

## Troubleshooting

### Problem: No face detected

**Symptoms:**
- Video feed shows, but no red/green box around face
- "Waiting for someone to appear..." message

**Solutions:**
1. **Improve lighting** - Face detection needs good lighting
2. **Face camera directly** - Look straight at camera
3. **Check distance** - Be 2-4 feet from camera
4. **Clean camera lens** - Remove any obstructions
5. **Test camera:** `python3 utils/detect_face.py`

### Problem: Name not extracted from speech

**Symptoms:**
- Speech transcribed correctly
- But learning card doesn't appear
- "Unknown - Listening..." stays on screen

**Solutions:**
1. **Speak clearly** - Enunciate your name
2. **Use clear patterns:**
   - ✅ "My name is Sarah Johnson"
   - ✅ "I'm Sarah, the daughter"
   - ❌ "It's me" (too vague)
   - ❌ "Sarah here" (might work, but less reliable)
3. **Check confidence** - System needs 60%+ confidence
4. **Repeat introduction** - Try saying your name again
5. **Check transcript** - Verify speech is being transcribed

### Problem: Face samples not collecting

**Symptoms:**
- Progress shows 0/10 or stuck at low number
- No progress bar movement

**Solutions:**
1. **Stay in frame** - Keep face in camera view
2. **Move slightly** - System collects different angles
3. **Check face detection** - Red box should be visible
4. **Verify unknown face** - Should show "Unknown" label
5. **Check console logs** - Look for errors in terminal

### Problem: Audio not working

**Symptoms:**
- No transcript appearing
- "Listening for conversation..." message persists

**Solutions:**
1. **Check microphone permissions**
   - macOS: System Preferences → Security & Privacy → Microphone
   - Allow Terminal/Python access
2. **Test audio input:**
   ```bash
   python3 utils/live_transcribe.py
   ```
3. **Check sounddevice:**
   ```python
   import sounddevice as sd
   print(sd.query_devices())
   ```
4. **Try different audio device** - Edit audio device index
5. **Check volume** - Speak louder or closer to microphone

### Problem: Enrollment fails

**Symptoms:**
- Click "Enroll" button
- Error message appears

**Solutions:**
1. **Check sample count** - Need 10+ samples
2. **Verify database** - Ensure remind.db is writable
3. **Check logs** - Look for errors in terminal
4. **Try manual enrollment:**
   ```bash
   python3 apps/quick_enroll.py --name "Sarah Johnson"
   ```
5. **Check disk space** - Ensure enough space for database

### Problem: Recognition not working after enrollment

**Symptoms:**
- Person enrolled successfully
- But not recognized when they return

**Solutions:**
1. **Check lighting** - Same lighting as enrollment?
2. **Collect more samples** - Re-enroll with 15-20 samples
3. **Check tolerance** - May need to adjust (see Configuration)
4. **Verify database:**
   ```bash
   python3 tests/test_database.py
   ```
5. **Test recognition:**
   ```bash
   python3 utils/recognize.py
   ```

---

## Best Practices

### For Best Results

1. **Good Lighting**
   - Natural light or bright indoor lighting
   - Avoid backlighting (don't stand in front of window)
   - No harsh shadows on face

2. **Clear Speech**
   - Speak at normal volume
   - Face the microphone
   - Use clear introduction phrases
   - Spell unusual names: "My name is Saoirse, spelled S-A-O-I-R-S-E"

3. **Face Sample Collection**
   - Look directly at camera
   - Move head slightly (different angles)
   - Don't move too fast
   - Keep face in frame entire time
   - Aim for 15-20 samples for best accuracy

4. **Enrollment**
   - Use real names (not nicknames initially)
   - Specify relationship clearly
   - Enroll in typical lighting conditions
   - Re-enroll if appearance changes (glasses, beard, etc.)

### Privacy Considerations

1. **Data Storage**
   - All data stored locally in `remind.db`
   - No cloud upload
   - Face encodings are mathematical vectors, not images
   - Raw video frames not saved (only encodings)

2. **Consent**
   - Obtain consent before enrolling someone
   - Explain what data is collected
   - Allow users to be deleted from system

3. **Security**
   - Keep `remind.db` file secure
   - Regular backups
   - Consider encrypting database for production use
   - Don't share database files

---

## Advanced Usage

### Integrate with Your App

Use the REST API to integrate ReMind with other applications:

```python
import requests

# Check who's in front of camera
response = requests.get('http://localhost:5001/api/current_person')
data = response.json()

if data['status'] == 'recognized':
    name = data['person']['name']
    print(f"Hello, {name}!")
elif data['status'] == 'learning':
    print(f"Learning: {data['candidate']['name']}")
```

### Batch Enrollment

If you have existing data, you can batch enroll:

```python
from database import FaceRecognitionManager
import cv2

people = [
    {"name": "Sarah", "relationship": "Daughter", "video_path": "sarah.mp4"},
    {"name": "John", "relationship": "Son", "video_path": "john.mp4"},
]

mgr = FaceRecognitionManager()

for person in people:
    # Load video or capture from camera
    cap = cv2.VideoCapture(person['video_path'])
    frames = []

    for _ in range(20):
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()

    # Enroll
    mgr.enroll_person(
        frames=frames,
        name=person['name'],
        relationship=person['relationship']
    )
```

### Export/Import Database

**Backup:**
```bash
cp remind.db backups/remind_$(date +%Y%m%d).db
```

**Restore:**
```bash
cp backups/remind_20231115.db remind.db
```

**Export to JSON:**
```python
from database import PersonDatabase
import json

db = PersonDatabase()
people = db.list_all_people()

with open('people_export.json', 'w') as f:
    json.dump([dict(p) for p in people], f, indent=2)
```

---

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Browser                          │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐│
│  │ Video Feed│  │Person Info   │  │ Transcript Display   ││
│  │           │  │ Panel        │  │                      ││
│  └───────────┘  └──────────────┘  └──────────────────────┘│
└────────────┬────────────────────────────────────────────────┘
             │ HTTP/REST API (Flask)
             │
┌────────────▼────────────────────────────────────────────────┐
│                     Flask Web Server                        │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐│
│  │ Video Stream │  │ API Endpoints   │  │ Audio Stream   ││
│  │ Generator    │  │ /api/*          │  │ Processing     ││
│  └──────┬───────┘  └─────────────────┘  └────────┬───────┘│
└─────────┼──────────────────────────────────────────┼────────┘
          │                                          │
          ▼                                          ▼
┌─────────────────────┐                  ┌──────────────────┐
│ FaceRecognitionMgr  │                  │ Whisper AI       │
│ - detect_faces()    │                  │ - transcribe()   │
│ - recognize_face()  │                  │                  │
│ - enroll_person()   │                  │ ContextExtractor │
└─────────┬───────────┘                  │ - suggest_new_   │
          │                              │   person()       │
          │                              └──────────┬───────┘
          │                                         │
          ▼                                         ▼
┌──────────────────────────────────────────────────────────┐
│                    SQLite Database                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ people      │  │ encounters   │  │ topics         │ │
│  │ - id        │  │ - id         │  │ - topic_text   │ │
│  │ - name      │  │ - person_id  │  │ - category     │ │
│  │ - encoding  │  │ - transcript │  │ - frequency    │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Threading Model

```
Main Thread
├── Flask HTTP Server
│   ├── Video Frame Generation
│   └── API Request Handling
│
Audio Thread (Daemon)
├── Audio Capture (sounddevice)
├── Speech Recognition (Whisper)
├── Transcript Updates
└── Metadata Extraction
```

### Face Recognition Pipeline

```
1. Frame Capture
   └─→ cv2.VideoCapture()

2. Face Detection
   └─→ face_recognition.face_locations()
   └─→ Returns: [(x, y, w, h), ...]

3. Face Encoding
   └─→ face_recognition.face_encodings()
   └─→ Returns: 128-d numpy array

4. Face Comparison
   └─→ face_recognition.compare_faces()
   └─→ Returns: [True/False, ...]

5. Distance Calculation
   └─→ face_recognition.face_distance()
   └─→ Returns: [0.0-1.0, ...]
   └─→ < 0.6 = Match

6. Database Lookup
   └─→ PersonDatabase.get_person(id)
   └─→ Returns: person record
```

---

## Development

### Adding New Features

**Example: Add email extraction**

1. Update `database/context_extractor.py`:
```python
def suggest_new_person(text: str) -> dict:
    # ... existing code ...

    # Add email detection
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)

    if emails:
        result['email'] = emails[0]

    return result
```

2. Update `apps/web_app.py`:
```python
def auto_enroll_person():
    # ... existing code ...

    person_id = face_recognition.enroll_person(
        frames=samples_copy,
        name=name,
        relationship=relationship,
        email=learning_candidate.get('email'),  # Add this
        important_info=f"Auto-learned..."
    )
```

3. Update `web/templates/index.html` to display email

### Running Tests

```bash
# Test all components
python3 tests/test_auto_learning.py

# Test specific component
python3 tests/test_database.py

# Test face detection
python3 utils/detect_face.py

# Test speech recognition
python3 utils/live_transcribe.py
```

---

## FAQ

**Q: Can I use this without internet?**
A: Yes! Whisper AI runs locally. No internet needed after initial model download.

**Q: What if someone has the same name?**
A: System uses face encoding as unique identifier. Two "John Smith" entries are fine.

**Q: Can I delete someone from the database?**
A: Yes. Use `PersonDatabase.delete_person(person_id)` or add a UI button.

**Q: How accurate is the face recognition?**
A: 95-99% with good enrollment (15+ samples, good lighting).

**Q: Does it work with glasses/beard/hat?**
A: Glasses: Yes. Beard growth: Usually yes. Hat: Depends (avoid covering face).

**Q: Can multiple people be in frame?**
A: System detects all faces but currently focuses on the first/largest face.

**Q: How much storage does it use?**
A: ~5-10 KB per person (face encoding + metadata). 1000 people ≈ 10 MB.

**Q: Can I use this in production?**
A: For personal/testing: Yes. For healthcare/commercial: Ensure HIPAA/GDPR compliance.

---

## Support

**Documentation:**
- [README.md](../README.md) - Project overview
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design

**Testing:**
- `python3 tests/test_auto_learning.py` - Comprehensive test suite
- `python3 tests/test_database.py` - Database tests

**Utilities:**
- `python3 utils/detect_face.py` - Test face detection
- `python3 utils/live_transcribe.py` - Test speech recognition
- `python3 utils/recognize.py` - Test face recognition

---

**Made with ❤️ for accessible dementia care**

*ReMind - Learning to remember, one conversation at a time*