# ReMind V2 - Complete Setup Guide

## 🎯 What's New in V2

ReMind V2 is a complete overhaul with proper face recognition integration:

### ✨ New Features:
1. **Deep Learning Face Recognition** - Uses `face_recognition` library (based on dlib)
2. **Direct Database Integration** - Face encodings stored in SQLite database
3. **In-App Face Enrollment** - Add new people without retraining
4. **Web Interface** - Beautiful web UI showing person info in real-time
5. **Rich Person Profiles** - Display name, relationship, phone, important info, visit history, and discussion topics

### 🔄 What Changed:
- **Old System**: LBPH face recognition with separate files (`face_recognizer.yml`, `labels.json`)
- **New System**: Deep learning embeddings stored directly in database
- **No More Manual Training**: Enroll faces on-the-fly during encounters

---

## 📦 Installation

### Step 1: Install System Dependencies

#### macOS:
```bash
# Install CMake (required for dlib)
brew install cmake

# Install dlib
pip3 install dlib
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y cmake python3-dev
sudo apt-get install -y libopenblas-dev liblapack-dev
```

### Step 2: Install Python Dependencies

```bash
cd /Users/adhitya/Development/ReMind/face_detection

# Install all requirements
pip3 install -r requirements.txt
```

**Note**: Installing `dlib` can take 5-10 minutes as it compiles from source.

### Step 3: Verify Installation

```bash
python3 -c "import face_recognition; print('✅ face_recognition installed')"
python3 -c "import cv2; print('✅ OpenCV installed')"
python3 -c "import whisper; print('✅ Whisper installed')"
```

---

## 🚀 Quick Start

### Option 1: Desktop App with In-Video Display

Run the enhanced ReMind Assistant with person info overlaid on video:

```bash
python3 remind_assistant_v2.py
```

**Controls:**
- `e` - Start face enrollment mode
- `n` - Complete enrollment (after collecting samples)
- `s` - Save encounter summary
- `q` - Quit

### Option 2: Web Interface (Recommended for Caregivers)

Run the web app for a beautiful browser-based interface:

```bash
python3 web_app.py
```

Then open in browser: **http://localhost:5000**

The web interface shows:
- Live video feed with face detection
- Real-time person information panel
- Contact details, important notes
- Visit history and discussion topics

---

## 👥 Enrolling People

### Method 1: During Live Session (In-App)

1. Start the assistant:
   ```bash
   python3 remind_assistant_v2.py
   ```

2. Press `e` to enter enrollment mode

3. Position the person's face in the camera (system will collect 20 samples automatically)

4. Press `n` when ready, then enter:
   - Name
   - Relationship (e.g., "Daughter", "Nurse", "Friend")
   - Important information (e.g., "Brings medication on Tuesdays")

5. Done! Person is now in the database and will be recognized immediately

### Method 2: Using Python Script

Create a simple enrollment script:

```python
from database import FaceRecognitionManager
import cv2

face_mgr = FaceRecognitionManager("remind.db")
cap = cv2.VideoCapture(0)

frames = []
print("Collecting face samples... (capturing 15 frames)")

while len(frames) < 15:
    ret, frame = cap.read()
    if ret:
        frames.append(frame)
        cv2.imshow("Enrollment", frame)
        cv2.waitKey(100)

cap.release()
cv2.destroyAllWindows()

# Enroll the person
person_id = face_mgr.enroll_person(
    frames=frames,
    name="Sarah Johnson",
    relationship="Daughter",
    phone="555-1234",
    important_info="Brings medication every Tuesday morning"
)

print(f"✅ Enrolled! Person ID: {person_id}")
```

### Method 3: Add Person Info Later

You can add a person to the database without a face first:

```python
from database import PersonDatabase

db = PersonDatabase("remind.db")

person_id = db.add_person(
    name="Dr. Smith",
    relationship="Primary Care Physician",
    phone="555-9876",
    email="dr.smith@clinic.com",
    important_info="Visits every 2 weeks for health checkup",
    notes="Patient has been seeing Dr. Smith for 5 years"
)

print(f"Added person ID: {person_id}")
# Later, you can add their face encoding using enrollment
```

---

## 🎨 Web Interface Features

The web interface (`web_app.py`) provides:

### Real-Time Display:
- **Live video feed** with face detection boxes
- **Person card** showing name, relationship, match confidence
- **Important information** highlighted in yellow box
- **Contact details** (phone, email)
- **Visit statistics** (total visits, last seen)
- **Discussion topics** with frequency counts
- **Caregiver notes**

### API Endpoints:
- `GET /api/current_person` - Current recognized person
- `GET /api/people` - List all enrolled people
- `GET /api/person/<id>` - Detailed person info
- `POST /api/add_person` - Add new person
- `PUT /api/update_person/<id>` - Update person info
- `GET /api/encounters/today` - Today's encounters

---

## 📊 Database Structure

### People Table:
```sql
- id: Person ID
- name: Full name
- relationship: e.g., "Daughter", "Nurse"
- face_encoding: 128-d face embedding (BLOB)
- phone, email, address: Contact info
- important_info: Critical notes
- notes: General notes
- typical_topics: JSON array of common topics
- first_seen, last_updated: Timestamps
```

### Encounters Table:
```sql
- id: Encounter ID
- person_id: Foreign key to people
- start_time, end_time, duration
- full_transcript: Complete conversation
- summary: AI-generated summary
- key_topics: JSON topics discussed
- mentioned_dates, action_items: Extracted info
```

---

## 🔧 Advanced Configuration

### Adjust Face Recognition Tolerance

Lower = stricter matching (fewer false positives, might miss some matches)
Higher = looser matching (more false positives, catches more variations)

```python
face_mgr = FaceRecognitionManager("remind.db", tolerance=0.6)  # Default
# tolerance=0.5 for stricter
# tolerance=0.7 for looser
```

### Change Whisper Model

```bash
# Faster, less accurate:
python3 remind_assistant_v2.py --model tiny

# More accurate, slower:
python3 remind_assistant_v2.py --model base
python3 remind_assistant_v2.py --model small
```

### Use Different Camera

```python
# In the code, change:
cap = cv2.VideoCapture(0)  # Default camera
cap = cv2.VideoCapture(1)  # External camera
```

---

## 🎯 Usage Workflow

### Daily Caregiver Workflow:

1. **Morning Setup**:
   ```bash
   python3 web_app.py
   ```
   Open browser to http://localhost:5000

2. **When Person Arrives**:
   - System automatically recognizes face
   - Information panel updates with their details
   - Important notes are highlighted
   - Previous visit topics shown for context

3. **New Visitor**:
   - If face not recognized, use enrollment mode
   - Or run desktop app and press `e` to enroll

4. **End of Day**:
   - Review encounter summaries in database
   - Check discussion topics to track patterns

### Medical Professional Workflow:

1. View patient's encounter history:
   ```python
   from database import EncounterDatabase

   db = EncounterDatabase("remind.db")
   encounters = db.get_recent_encounters(person_id=1, limit=10)

   for enc in encounters:
       print(f"Date: {enc['start_time']}")
       print(f"Summary: {enc['summary']}")
       print(f"Topics: {enc['key_topics']}")
   ```

2. Check for concerning patterns (confusion, repetitive questions)

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'face_recognition'"

**Solution**:
```bash
pip3 install face_recognition
# If it fails, install dlib first:
pip3 install dlib
```

### "SQLite objects created in a thread can only be used in that same thread"

**Solution**: Already fixed in V2! We added `check_same_thread=False` and thread locks.

### "Camera not opening" / "Cannot open camera"

**Solutions**:
1. Check camera index:
   ```python
   cap = cv2.VideoCapture(0)  # Try 0, 1, 2...
   ```

2. On macOS, grant camera permissions:
   - System Preferences → Security & Privacy → Camera
   - Allow Terminal/your IDE

3. Check if camera is in use by another app

### Face recognition is slow

**Solutions**:
1. Use GPU acceleration (if available)
2. Reduce video resolution
3. Skip frames (process every 2nd or 3rd frame)

### Person not being recognized

**Solutions**:
1. Check enrollment quality - need good lighting
2. Enroll with more samples (15-20 instead of 10)
3. Reduce tolerance: `FaceRecognitionManager(tolerance=0.55)`
4. Re-enroll with better quality images

---

## 📈 Performance Tips

### For Faster Recognition:
```python
# In face_recognition_db.py, use HOG instead of CNN for detection:
face_locations = face_recognition.face_locations(rgb_frame, model="hog")
# "hog" is faster, "cnn" is more accurate
```

### For Better Accuracy:
- Enroll with varied lighting conditions
- Capture samples from different angles
- Update face encodings periodically as person ages

---

## 🔒 Security & Privacy

### Database Encryption:
Consider encrypting the database file containing face encodings:

```bash
# Using SQLCipher
pip3 install sqlcipher3
```

### Access Control:
- Limit web app access to local network only
- Use authentication for production deployments
- Store database in secure location

---

## 📝 Example: Complete Daily Session

```bash
# 1. Start web interface
python3 web_app.py

# 2. Open browser: http://localhost:5000

# 3. System automatically recognizes people and shows:
#    - Name and relationship
#    - When they last visited
#    - What you discussed before
#    - Important notes (medications, appointments, etc.)

# 4. New person arrives:
#    - Shows "Unknown Person"
#    - Switch to desktop app to enroll:
#      python3 remind_assistant_v2.py
#    - Press 'e', collect samples, press 'n', enter details
#    - Return to web interface - person now recognized!

# 5. End of day:
#    - Press 's' to save encounter summaries
#    - Or just close - auto-saves on exit
```

---

## 🎓 Next Steps

1. **Customize the UI**: Edit `templates/index.html` for your branding
2. **Add more fields**: Extend the database schema for medical history, preferences, etc.
3. **Integration**: Connect with electronic health records (EHR)
4. **Mobile app**: Build React Native app using the Flask API
5. **Voice commands**: Add voice control for hands-free operation

---

## 💡 Tips for Best Results

1. **Enrollment**:
   - Good lighting is crucial
   - Capture from multiple angles
   - Ask person to smile, look serious, etc. for variety
   - Update encodings every few months

2. **Important Info**:
   - Be specific: "Allergic to penicillin" not just "allergies"
   - Include context: "Daughter Sarah visits Tuesday evenings"
   - Update regularly

3. **Database Maintenance**:
   - Backup regularly: `cp remind.db remind_backup_$(date +%Y%m%d).db`
   - Archive old encounters to keep database fast
   - Review and update person info periodically

---

## 🆘 Support

For issues or questions:
1. Check this guide first
2. Review code comments in `remind_assistant_v2.py`
3. Check database schema in `database/schema.sql`
4. Test individual components (face recognition, database, etc.) separately

Enjoy using ReMind V2! 🧠✨
