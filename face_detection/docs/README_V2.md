# ReMind V2 - Advanced Memory Assistant for Dementia Care

## 🌟 Overview

ReMind V2 is a comprehensive AI-powered memory assistant designed for dementia care. It combines advanced face recognition, speech transcription, and contextual memory to help patients recognize and remember important people in their lives.

### Key Features

✅ **Deep Learning Face Recognition** - Accurate face detection and recognition using state-of-the-art models
✅ **Real-Time Person Information** - Instantly displays name, relationship, and important details
✅ **Database-Driven** - All data stored in SQLite for easy access and management
✅ **In-App Face Enrollment** - Add new people without complex training procedures
✅ **Web Interface** - Beautiful browser-based UI for caregivers
✅ **Speech Transcription** - Real-time conversation recording with Whisper AI
✅ **Context Extraction** - Automatically identifies topics, dates, and action items
✅ **Visit Tracking** - Records all encounters with timestamps and summaries
✅ **Discussion Memory** - Remembers what was talked about in previous visits

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd face_detection
pip3 install -r requirements.txt
```

**Note**: Installing `dlib` may take several minutes.

### 2. Enroll Your First Person

```bash
python3 quick_enroll.py \
  --name "Sarah Johnson" \
  --relationship "Daughter" \
  --phone "555-1234" \
  --info "Brings medication on Tuesdays"
```

This will:
- Open your camera
- Capture 15 face samples automatically
- Save to database with all details
- Person is now ready to be recognized!

### 3. Start the System

#### Option A: Desktop App (Info Overlaid on Video)

```bash
python3 remind_assistant_v2.py
```

Shows live video with person information floating near their face!

#### Option B: Web Interface (Recommended)

```bash
python3 web_app.py
```

Then open: **http://localhost:5000**

Beautiful web interface showing:
- Live video feed
- Person information panel
- Contact details
- Visit history
- Discussion topics

---

## 📁 Project Structure

```
face_detection/
├── remind_assistant_v2.py      # Main desktop application
├── web_app.py                   # Web interface
├── quick_enroll.py              # Quick enrollment tool
├── database/
│   ├── face_recognition_db.py  # Face recognition + DB integration
│   ├── person_db.py             # Person management
│   ├── encounter_db.py          # Encounter/visit tracking
│   ├── context_extractor.py    # AI context extraction
│   └── schema.sql               # Database schema
├── templates/
│   └── index.html               # Web interface template
├── requirements.txt             # Python dependencies
├── SETUP_GUIDE.md              # Detailed setup instructions
└── README_V2.md                # This file
```

---

## 🎯 How It Works

### 1. Face Recognition Pipeline

```
Camera Frame → Face Detection (Haar Cascade)
            → Face Encoding (dlib CNN)
            → Database Matching
            → Person Recognition
            → Display Information
```

### 2. Database Integration

- **Face encodings** stored as 128-d vectors in database (BLOB)
- **Person info** (name, relationship, contact, notes) in `people` table
- **Encounters** logged with timestamps, transcripts, summaries
- **Topics** tracked across visits for pattern recognition

### 3. Enrollment Workflow

```
New Person → Capture 15+ samples → Generate average encoding
          → Store in database → Immediate recognition
```

No separate training step needed!

---

## 💻 Usage Examples

### Enroll Multiple People

```bash
# Daughter
python3 quick_enroll.py \
  --name "Sarah Johnson" \
  --relationship "Daughter" \
  --phone "555-1234" \
  --info "Visits Tuesday evenings, brings groceries"

# Nurse
python3 quick_enroll.py \
  --name "Maria Garcia" \
  --relationship "Home Health Nurse" \
  --phone "555-5678" \
  --info "Administers medications, Monday/Wednesday/Friday mornings"

# Friend
python3 quick_enroll.py \
  --name "Robert Chen" \
  --relationship "Friend and neighbor" \
  --info "Lives next door, checks in daily"
```

### Programmatic Enrollment

```python
from database import FaceRecognitionManager
import cv2

# Capture frames
cap = cv2.VideoCapture(0)
frames = []
for i in range(15):
    ret, frame = cap.read()
    if ret:
        frames.append(frame)
cap.release()

# Enroll
face_mgr = FaceRecognitionManager("remind.db")
person_id = face_mgr.enroll_person(
    frames=frames,
    name="Dr. James Smith",
    relationship="Primary Care Physician",
    phone="555-9999",
    email="dr.smith@clinic.com",
    important_info="Visits every 2 weeks for checkups"
)

print(f"Enrolled with ID: {person_id}")
```

### Query Database

```python
from database import PersonDatabase, EncounterDatabase

# List all people
person_db = PersonDatabase("remind.db")
people = person_db.list_all_people()

for person in people:
    print(f"{person['name']} - {person['relationship']}")

# Get encounter history
encounter_db = EncounterDatabase("remind.db")
encounters = encounter_db.get_recent_encounters(person_id=1, limit=5)

for enc in encounters:
    print(f"{enc['start_time']}: {enc['summary']}")
```

---

## 🎨 Web Interface Features

### Main Display

- **Live Video Feed**: Real-time camera with face detection boxes
- **Person Card**: Name, relationship, match confidence percentage
- **Important Info**: Highlighted warnings (allergies, medications, etc.)
- **Contact Details**: Phone and email for easy reference
- **Visit Statistics**: Total visits, last seen time
- **Discussion Topics**: What you've talked about before with frequency

### API Endpoints

All data accessible via REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/current_person` | GET | Currently recognized person |
| `/api/people` | GET | List all enrolled people |
| `/api/person/<id>` | GET | Detailed info for person |
| `/api/add_person` | POST | Add new person |
| `/api/update_person/<id>` | PUT | Update person info |
| `/api/encounters/today` | GET | Today's encounters |

Example API call:
```bash
curl http://localhost:5000/api/current_person
```

---

## 🔧 Configuration

### Adjust Recognition Sensitivity

In `face_recognition_db.py`:

```python
FaceRecognitionManager(db_path, tolerance=0.6)
```

- `tolerance=0.5` - Stricter (fewer false matches)
- `tolerance=0.6` - Default (balanced)
- `tolerance=0.7` - Looser (catches more variations)

### Change Whisper Model

```bash
# Faster transcription (less accurate)
python3 remind_assistant_v2.py --model tiny

# Better accuracy (slower)
python3 remind_assistant_v2.py --model base
python3 remind_assistant_v2.py --model small
```

### Use Different Camera

```python
# In code, change camera index:
cv2.VideoCapture(0)  # Built-in camera
cv2.VideoCapture(1)  # External USB camera
```

---

## 📊 What's Stored in the Database

### People Table
- Basic info: name, relationship
- Contact: phone, email, address
- Face encoding: 128-d vector
- Important info: medications, allergies, special notes
- Metadata: first seen, last updated

### Encounters Table
- Person ID (who visited)
- Timestamps: start, end, duration
- Full transcript of conversation
- AI-generated summary
- Extracted topics, dates, action items
- Mood and confusion indicators

### Topics Table
- Topic text and category
- Frequency count
- Last mentioned timestamp

---

## 🎓 Use Cases

### For Dementia Patients
- **Instant Recognition**: See name and relationship when someone visits
- **Memory Aids**: Remember what you talked about last time
- **Important Reminders**: Critical info displayed (e.g., "This is your nurse who gives medication")

### For Caregivers
- **Visit Tracking**: Know who visited and when
- **Conversation Logs**: Review what was discussed
- **Pattern Recognition**: Identify confusion, repetitive questions
- **Handoff Notes**: Share context with other caregivers

### For Medical Professionals
- **Patient History**: Review encounter summaries
- **Cognitive Assessment**: Track confusion levels over time
- **Care Planning**: Identify frequently mentioned topics/concerns

---

## 🔒 Privacy & Security

### Data Storage
- All data stored locally in SQLite database
- Face encodings are mathematical vectors, not images
- No data sent to cloud/external servers

### Recommendations
1. **Encrypt database**: Use SQLCipher for sensitive deployments
2. **Access control**: Limit web app to local network
3. **Regular backups**: `cp remind.db backup_$(date +%Y%m%d).db`
4. **Audit logs**: Track who accesses patient data

---

## 🐛 Troubleshooting

### "Cannot open camera"
- Check camera permissions (macOS: System Preferences → Security → Camera)
- Verify camera index (try 0, 1, 2...)
- Close other apps using camera

### "ModuleNotFoundError: face_recognition"
```bash
# Install dlib first (may take 5-10 minutes)
pip3 install dlib
pip3 install face_recognition
```

### Person not recognized
- Re-enroll with better lighting
- Capture more samples (20 instead of 15)
- Adjust tolerance parameter
- Check if face encoding exists: `person_db.get_person(id)['face_encoding']`

### Web interface not loading
- Check Flask is running: `python3 web_app.py`
- Try http://127.0.0.1:5000 instead of localhost
- Check firewall settings

---

## 📈 Performance Optimization

### For Faster Recognition
- Use HOG face detection instead of CNN (edit `face_recognition_db.py`)
- Process every 2nd or 3rd frame instead of all
- Reduce video resolution

### For Better Accuracy
- Enroll with good lighting and multiple angles
- Use `model="cnn"` for face detection (slower but more accurate)
- Capture 20-30 samples during enrollment
- Re-enroll periodically as person ages/changes appearance

---

## 🚧 Future Enhancements

### Planned Features
- [ ] Voice recognition for speaker identification
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Medication reminders
- [ ] Emergency contact quick dial
- [ ] Photo albums/memory triggers
- [ ] Integration with EHR systems
- [ ] Cloud sync (optional)

### Contribute
This is an open project! Feel free to:
- Add new features
- Improve UI/UX
- Optimize performance
- Add translations
- Write documentation

---

## 📝 Complete Example Workflow

### Scenario: Setting up for elderly patient "Mary"

#### 1. Initial Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Verify installation
python3 -c "import face_recognition; print('Ready!')"
```

#### 2. Enroll Family Members
```bash
# Daughter Sarah
python3 quick_enroll.py \
  --name "Sarah Williams" \
  --relationship "Daughter" \
  --phone "555-1234" \
  --info "Visits Tuesday/Thursday evenings. Has power of attorney."

# Son Michael
python3 quick_enroll.py \
  --name "Michael Williams" \
  --relationship "Son" \
  --phone "555-5678" \
  --info "Lives nearby, handles finances. Visits weekends."

# Home Health Aide
python3 quick_enroll.py \
  --name "Jennifer Lopez" \
  --relationship "Home Health Aide" \
  --phone "555-9012" \
  --info "Administers medications 9AM and 6PM daily."
```

#### 3. Start Web Interface
```bash
python3 web_app.py
```

#### 4. Daily Use
- Open browser: http://localhost:5000
- When someone visits, their info appears automatically
- Patient sees: "This is Sarah (Your Daughter)"
- Important info displayed: "Has power of attorney"
- Shows: "You last talked 2 days ago about: Upcoming doctor appointment, Garden flowers"

#### 5. Review Encounters
```python
from database import EncounterDatabase

db = EncounterDatabase("remind.db")
encounters = db.get_todays_encounters()

for enc in encounters:
    print(f"Visit from {enc['name']} at {enc['start_time']}")
    print(f"Discussed: {enc['key_topics']}")
    print(f"Summary: {enc['summary']}")
```

---

## 🎉 Benefits

### For Patients
- ✅ Reduced anxiety from not recognizing visitors
- ✅ Improved social engagement
- ✅ Better medication compliance (recognizes healthcare workers)
- ✅ Maintains dignity and independence

### For Caregivers
- ✅ Better care coordination
- ✅ Detailed visit logs
- ✅ Early detection of cognitive changes
- ✅ Peace of mind

### For Families
- ✅ Stay connected even when memory fails
- ✅ Track care quality
- ✅ Preserve conversation history
- ✅ Share care responsibilities easily

---

## 📞 Support

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)

For technical details, check the code comments in:
- `remind_assistant_v2.py` - Main application logic
- `database/face_recognition_db.py` - Face recognition implementation
- `web_app.py` - Web interface and API

---

## 📜 License

This project is for educational and care purposes. Please ensure compliance with healthcare privacy regulations (HIPAA, GDPR, etc.) when deploying in production environments.

---

**Made with ❤️ for better dementia care**

*ReMind - Because every person deserves to be remembered*
