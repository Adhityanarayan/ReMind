# ReMind V2 - Memory Assistant for Dementia Care

![ReMind Logo](https://img.shields.io/badge/ReMind-V2.0-blue)
![Python](https://img.shields.io/badge/Python-3.7%2B-green)
![License](https://img.shields.io/badge/License-Educational-orange)

> Advanced face recognition and memory assistance system for dementia patients

---

## 🎯 Quick Start

### Install Dependencies
```bash
./install.sh
# OR
pip3 install -r requirements.txt
```

### Enroll Your First Person
```bash
python3 apps/quick_enroll.py \
  --name "Sarah Johnson" \
  --relationship "Daughter" \
  --info "Brings medication on Tuesdays"
```

### Launch the System

**Option 1: Web Interface** (Recommended)
```bash
python3 apps/web_app.py
# Open http://localhost:5001 in browser
```

**Option 2: Desktop App**
```bash
python3 apps/remind_assistant_v2.py
```

---

## 📁 Project Structure

```
face_detection/
│
├── apps/                          # Main Applications
│   ├── remind_assistant_v2.py    # Desktop app with AR-style overlays
│   ├── web_app.py                # Web interface with live video
│   └── quick_enroll.py           # Quick enrollment tool
│
├── database/                      # Database Layer
│   ├── face_recognition_db.py    # Face recognition + DB integration
│   ├── person_db.py              # Person management
│   ├── encounter_db.py           # Encounter/visit tracking
│   ├── context_extractor.py      # AI context extraction
│   ├── schema.sql                # Database schema
│   └── __init__.py               # Package exports
│
├── web/                           # Web Interface Assets
│   └── templates/
│       └── index.html            # Web UI template
│
├── utils/                         # Utility Scripts
│   ├── detect_camera.py          # Test camera functionality
│   ├── detect_face.py            # Test face detection
│   ├── detect_image.py           # Test on images
│   ├── recognize.py              # Test recognition
│   ├── live_transcribe.py        # Test audio transcription
│   └── save_transcription.py     # Save audio to text
│
├── legacy/                        # Legacy V1 Files
│   ├── remind_assistant.py       # Original LBPH-based assistant
│   ├── combined_demo.py          # Old combined demo
│   ├── collect_faces.py          # Old manual face collection
│   └── train_recognizer.py       # Old LBPH training
│
├── tests/                         # Test Files
│   ├── test_database.py          # Database tests
│   ├── test_thread_fix.py        # Threading tests
│   └── try_import_cv.py          # OpenCV import test
│
├── docs/                          # Documentation
│   ├── README_V2.md              # Complete documentation
│   ├── SETUP_GUIDE.md            # Detailed setup guide
│   ├── ARCHITECTURE.md           # System architecture
│   ├── BUG_FIX_ENCOUNTER.md      # Bug fix notes
│   ├── QUICKSTART_TRANSCRIPTION.md
│   ├── TRANSCRIPTION_README.md
│   └── README_TIPS.md
│
├── scripts/                       # Helper Scripts
│   └── (future scripts)
│
├── requirements.txt               # Python dependencies
├── install.sh                     # Automated installer
├── LICENSE.txt                    # License file
└── README.md                      # This file
```

---

## 🌟 Features

### ✅ Core Functionality
- **Deep Learning Face Recognition** - 95-99% accuracy using dlib CNN
- **Database Integration** - Face encodings stored in SQLite
- **Real-Time Person Info** - Name, relationship, contact, important notes
- **Visit History** - Track all encounters with timestamps
- **Discussion Topics** - Remember what was talked about
- **Speech Transcription** - Real-time conversation logging (Whisper AI)
- **Context Extraction** - Auto-identify topics, dates, action items
- **🆕 Auto-Learning** - Automatically learns new people from conversation without pre-existing data!

### ✅ Interfaces
1. **Web Interface** (`apps/web_app.py`)
   - Browser-based UI
   - Live video feed
   - Person information panel
   - REST API

2. **Desktop App** (`apps/remind_assistant_v2.py`)
   - AR-style overlays
   - In-app enrollment
   - Speech transcription
   - Direct video display

3. **Quick Enrollment** (`apps/quick_enroll.py`)
   - Command-line tool
   - Fast person registration
   - Single-command operation

---

## 🚀 Usage

### Enrolling People

**Method 1: 🆕 Auto-Learning (Web App)** ⭐ NEW!
```bash
python3 apps/web_app.py
# Open http://localhost:5001
# Just introduce yourself: "Hello, my name is Sarah, I'm the daughter"
# System automatically learns from conversation!
```
See [docs/AUTO_LEARNING_GUIDE.md](docs/AUTO_LEARNING_GUIDE.md) for complete guide.

**Method 2: Quick Enroll (Command Line)**
```bash
python3 apps/quick_enroll.py \
  --name "Dr. James Smith" \
  --relationship "Primary Care Physician" \
  --phone "555-9999" \
  --info "Visits every 2 weeks for checkups"
```

**Method 3: Desktop App (Interactive)**
1. Run `python3 apps/remind_assistant_v2.py`
2. Press `e` to enter enrollment mode
3. Look at camera (system collects 20 samples)
4. Press `n` and enter details
5. Done!

**Method 3: Programmatic**
```python
from database import FaceRecognitionManager
import cv2

# Capture frames
cap = cv2.VideoCapture(0)
frames = [cap.read()[1] for _ in range(15)]
cap.release()

# Enroll
mgr = FaceRecognitionManager()
mgr.enroll_person(frames, "John Doe", "Friend")
```

### Using the Web Interface

```bash
python3 apps/web_app.py
```

Then open http://localhost:5001

Features:
- Live video stream with face detection
- Real-time person information updates
- Visit statistics and history
- Discussion topics from previous visits
- REST API for integration

### Using the Desktop App

```bash
python3 apps/remind_assistant_v2.py
```

Controls:
- `e` - Start enrollment mode
- `n` - Complete enrollment
- `s` - Save encounter summary
- `q` - Quit

---

## 🔧 Configuration

### Change Recognition Sensitivity
Edit `database/face_recognition_db.py`:
```python
FaceRecognitionManager(db_path, tolerance=0.6)
# 0.5 = stricter, 0.7 = looser
```

### Change Whisper Model
```bash
python3 apps/remind_assistant_v2.py --model tiny   # Fastest
python3 apps/remind_assistant_v2.py --model base   # Better
python3 apps/remind_assistant_v2.py --model small  # Best
```

### Change Camera
Edit camera index in apps:
```python
cv2.VideoCapture(0)  # Built-in camera
cv2.VideoCapture(1)  # External camera
```

---

## 📊 Database

All data stored in SQLite (`remind.db`):

**Tables:**
- `people` - Person information + face encodings
- `encounters` - Visit logs with transcripts
- `topics` - Discussion topics with frequency
- `reminders` - Medication/appointment reminders
- `activity_log` - General activity tracking

**Backup:**
```bash
cp remind.db backup_$(date +%Y%m%d).db
```

---

## 🛠️ Development

### Project Organization

- **apps/** - User-facing applications
- **database/** - Core data layer
- **web/** - Web interface assets
- **utils/** - Testing and utility tools
- **legacy/** - Old V1 code (reference only)
- **tests/** - Unit and integration tests
- **docs/** - All documentation
- **scripts/** - Helper scripts

### Adding New Features

1. Database changes → `database/schema.sql`
2. Face recognition → `database/face_recognition_db.py`
3. Person management → `database/person_db.py`
4. Encounter logging → `database/encounter_db.py`
5. Web API → `apps/web_app.py`
6. Desktop UI → `apps/remind_assistant_v2.py`

---

## 📖 Documentation

Comprehensive docs in `docs/` folder:

- **[docs/AUTO_LEARNING_GUIDE.md](docs/AUTO_LEARNING_GUIDE.md)** - 🆕 Auto-learning feature guide
- **[docs/README_V2.md](docs/README_V2.md)** - Complete feature overview
- **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Detailed installation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design
- **[docs/BUG_FIX_ENCOUNTER.md](docs/BUG_FIX_ENCOUNTER.md)** - Known issues

---

## 🔒 Privacy & Security

- All data stored locally (no cloud)
- Face encodings are mathematical vectors, not images
- Database encryption available (SQLCipher)
- HIPAA/GDPR considerations for production

---

## 🐛 Troubleshooting

### Camera Not Opening
```bash
# Test camera
python3 utils/detect_camera.py

# Try different index
python3 apps/web_app.py  # Edit camera index in code
```

### Import Errors
```bash
# Verify imports
python3 tests/try_import_cv.py

# Check path
cd face_detection  # Run from this directory
python3 apps/quick_enroll.py
```

### Face Recognition Issues
```bash
# Test on image first
python3 utils/detect_image.py path/to/image.jpg

# Check enrollment quality
# - Good lighting required
# - Multiple angles needed
# - 15+ samples recommended
```

---

## 🎓 Quick Examples

### List All Enrolled People
```python
from database import PersonDatabase

db = PersonDatabase()
people = db.list_all_people()
for p in people:
    print(f"{p['name']} - {p['relationship']}")
```

### Get Encounter History
```python
from database import EncounterDatabase

db = EncounterDatabase()
encounters = db.get_recent_encounters(person_id=1, limit=5)
for enc in encounters:
    print(f"{enc['start_time']}: {enc['summary']}")
```

### Test Face Recognition
```python
from database import FaceRecognitionManager
import cv2

mgr = FaceRecognitionManager()
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

person = mgr.recognize_face(frame)
if person:
    print(f"Recognized: {person['name']}")
```

---

## 📈 Performance

| Component | Speed | Accuracy |
|-----------|-------|----------|
| Face Detection | ~30 FPS | 85% |
| Face Recognition | ~5-10 FPS | 95-99% |
| Whisper Transcription | Real-time | 95%+ |
| Database Queries | <10ms | N/A |

**Hardware Recommendations:**
- CPU: Intel i5 or better
- RAM: 4GB minimum, 8GB recommended
- Camera: 720p or higher
- OS: macOS, Linux, or Windows (WSL)

---

## 🙏 Credits

Built with:
- [face_recognition](https://github.com/ageitgey/face_recognition) - Face recognition library
- [dlib](http://dlib.net/) - Machine learning toolkit
- [OpenCV](https://opencv.org/) - Computer vision library
- [Whisper](https://github.com/openai/whisper) - Speech recognition
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

## 📝 License

Educational use only. See LICENSE.txt for details.

For production deployment in healthcare settings, ensure compliance with:
- HIPAA (United States)
- GDPR (European Union)
- Local healthcare privacy regulations

---

## 🆘 Support

- 📖 Read the docs: `docs/SETUP_GUIDE.md`
- 🐛 Found a bug? Check `docs/BUG_FIX_ENCOUNTER.md`
- 💡 Need help? Review code comments in source files

---

**Made with ❤️ for better dementia care**

*ReMind - Because every person deserves to be remembered*