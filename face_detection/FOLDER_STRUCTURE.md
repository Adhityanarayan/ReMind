# ReMind V2 - Folder Structure Guide

## 📁 Complete Directory Tree

```
face_detection/
│
├── 📱 apps/                              # Main Applications
│   ├── remind_assistant_v2.py           # Desktop app with AR overlays
│   ├── web_app.py                        # Flask web interface
│   └── quick_enroll.py                   # CLI enrollment tool
│
├── 💾 database/                          # Data Layer
│   ├── __init__.py                       # Package exports
│   ├── face_recognition_db.py            # Face recognition manager
│   ├── person_db.py                      # Person CRUD operations
│   ├── encounter_db.py                   # Encounter logging
│   ├── context_extractor.py              # NLP context extraction
│   └── schema.sql                        # Database schema
│
├── 🌐 web/                               # Web Interface Assets
│   ├── templates/
│   │   └── index.html                    # Main web UI
│   └── static/                           # (future: CSS, JS, images)
│
├── 🔧 utils/                             # Utility & Testing Scripts
│   ├── detect_camera.py                  # Camera detection test
│   ├── detect_face.py                    # Face detection test
│   ├── detect_image.py                   # Image detection test
│   ├── recognize.py                      # Recognition test
│   ├── live_transcribe.py                # Audio transcription test
│   └── save_transcription.py             # Save audio to text
│
├── 📦 legacy/                            # Legacy V1 Code
│   ├── remind_assistant.py               # Original LBPH assistant
│   ├── combined_demo.py                  # Old demo
│   ├── collect_faces.py                  # Old face collection
│   └── train_recognizer.py               # Old LBPH training
│
├── 🧪 tests/                             # Test Files
│   ├── test_database.py                  # Database tests
│   ├── test_thread_fix.py                # Threading tests
│   └── try_import_cv.py                  # Import verification
│
├── 📚 docs/                              # Documentation
│   ├── README_V2.md                      # Complete docs
│   ├── SETUP_GUIDE.md                    # Installation guide
│   ├── ARCHITECTURE.md                   # System design
│   ├── BUG_FIX_ENCOUNTER.md              # Bug fixes log
│   ├── QUICKSTART_TRANSCRIPTION.md       # Transcription guide
│   ├── TRANSCRIPTION_README.md           # Audio setup
│   └── README_TIPS.md                    # Tips & tricks
│
├── 📝 scripts/                           # Helper Scripts
│   └── (future automation scripts)
│
├── 📄 README.md                          # Main README (this file)
├── 📄 FOLDER_STRUCTURE.md                # This file
├── 📄 requirements.txt                   # Python dependencies
├── 📄 LICENSE.txt                        # License
├── 🔧 install.sh                         # Installation script
│
└── 🗄️ remind.db                          # SQLite database (created at runtime)
```

---

## 📂 Folder Purposes

### `/apps` - Main Applications
**Purpose**: Production-ready user-facing applications

| File | Description | Usage |
|------|-------------|-------|
| `remind_assistant_v2.py` | Desktop application | `python3 apps/remind_assistant_v2.py` |
| `web_app.py` | Web interface (Flask) | `python3 apps/web_app.py` |
| `quick_enroll.py` | Fast enrollment CLI | `python3 apps/quick_enroll.py --name "..."` |

**When to use:**
- Running the actual ReMind system
- Production deployments
- End-user interactions

---

### `/database` - Core Data Layer
**Purpose**: All database operations and face recognition logic

| File | Responsibility |
|------|----------------|
| `face_recognition_db.py` | Face encoding, recognition, enrollment |
| `person_db.py` | CRUD operations for people |
| `encounter_db.py` | Visit logging and tracking |
| `context_extractor.py` | NLP context extraction from speech |
| `schema.sql` | Database table definitions |
| `__init__.py` | Package exports |

**When to modify:**
- Adding new database tables
- Changing face recognition algorithm
- Adding new person fields
- Modifying context extraction logic

**Import example:**
```python
from database import FaceRecognitionManager, PersonDatabase
```

---

### `/web` - Web Interface Assets
**Purpose**: HTML templates and static files for web UI

| Folder | Contains |
|--------|----------|
| `templates/` | HTML Jinja2 templates |
| `static/` | CSS, JavaScript, images (future) |

**When to modify:**
- Customizing web UI appearance
- Adding new web pages
- Changing layout/styling

---

### `/utils` - Utility Scripts
**Purpose**: Development, testing, and debugging tools

| File | Purpose |
|------|---------|
| `detect_camera.py` | Test camera functionality |
| `detect_face.py` | Test face detection |
| `detect_image.py` | Test on static images |
| `recognize.py` | Test face recognition |
| `live_transcribe.py` | Test audio transcription |
| `save_transcription.py` | Convert audio to text files |

**When to use:**
- Troubleshooting camera issues
- Testing individual components
- Development and debugging
- Verifying installation

**Example:**
```bash
# Test if camera works
python3 utils/detect_camera.py

# Test face detection on an image
python3 utils/detect_image.py photo.jpg
```

---

### `/legacy` - Legacy Code
**Purpose**: Old V1 code kept for reference

| File | Description |
|------|-------------|
| `remind_assistant.py` | Original LBPH-based system |
| `combined_demo.py` | Old demo combining features |
| `collect_faces.py` | Manual face sample collection |
| `train_recognizer.py` | LBPH model training |

**Note**: These files use the old architecture with separate training files.
**Do NOT use** for new development. Kept for:
- Understanding migration from V1 to V2
- Reference for specific implementations
- Backward compatibility if needed

---

### `/tests` - Test Files
**Purpose**: Unit tests and verification scripts

| File | Tests |
|------|-------|
| `test_database.py` | Database operations |
| `test_thread_fix.py` | Thread safety |
| `try_import_cv.py` | OpenCV imports |

**When to use:**
- Before committing changes
- After installation
- Debugging issues
- CI/CD pipelines

---

### `/docs` - Documentation
**Purpose**: All project documentation

| File | Content |
|------|---------|
| `README_V2.md` | Complete feature documentation |
| `SETUP_GUIDE.md` | Installation and configuration |
| `ARCHITECTURE.md` | System design and diagrams |
| `BUG_FIX_ENCOUNTER.md` | Bug tracking and fixes |
| `QUICKSTART_TRANSCRIPTION.md` | Quick audio setup |
| `TRANSCRIPTION_README.md` | Detailed audio guide |
| `README_TIPS.md` | Tips and best practices |

---

### `/scripts` - Helper Scripts
**Purpose**: Automation and maintenance scripts (future)

**Planned scripts:**
- Database backup automation
- Encounter export/import
- Batch enrollment
- Performance monitoring
- Database cleanup

---

## 🚀 Usage Patterns

### For End Users

```bash
# 1. Enroll people
python3 apps/quick_enroll.py --name "Sarah" --relationship "Daughter"

# 2. Run the system
python3 apps/web_app.py
# OR
python3 apps/remind_assistant_v2.py
```

### For Developers

```bash
# Test camera
python3 utils/detect_camera.py

# Test database
python3 tests/test_database.py

# Read documentation
cat docs/ARCHITECTURE.md
```

### For Troubleshooting

```bash
# Verify installation
python3 tests/try_import_cv.py

# Test individual components
python3 utils/detect_face.py
python3 utils/live_transcribe.py

# Check logs
cat docs/BUG_FIX_ENCOUNTER.md
```

---

## 📝 File Naming Conventions

### Applications (apps/)
- `*_v2.py` - Version 2 applications
- `web_*.py` - Web-related apps
- `quick_*.py` - Quick utility apps

### Database (database/)
- `*_db.py` - Database managers
- `*_extractor.py` - Data extraction utilities
- `schema.sql` - SQL schema files

### Utilities (utils/)
- `detect_*.py` - Detection tests
- `live_*.py` - Real-time utilities
- `save_*.py` - Saving utilities

### Tests (tests/)
- `test_*.py` - Unit tests
- `try_*.py` - Verification scripts

### Documentation (docs/)
- `README*.md` - README variants
- `*_GUIDE.md` - Guides
- All caps for important docs

---

## 🔄 Import Path Resolution

All apps use:
```python
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import FaceRecognitionManager
```

This allows:
- Running apps from `apps/` folder
- Importing from `database/` package
- Flexible project structure

---

## 📦 Python Package Structure

```
face_detection/                 # Project root
├── database/                   # Python package
│   └── __init__.py             # Exports: FaceRecognitionManager, etc.
└── apps/                       # Entry points
    └── *.py                    # Import from database
```

**Exports from `database/__init__.py`:**
```python
from .person_db import PersonDatabase
from .encounter_db import EncounterDatabase
from .face_recognition_db import FaceRecognitionManager
from .context_extractor import ContextExtractor
```

---

## 🎯 Quick Reference

### I want to...

**Run the system:**
- → `apps/remind_assistant_v2.py` or `apps/web_app.py`

**Add a new person:**
- → `apps/quick_enroll.py`

**Test camera:**
- → `utils/detect_camera.py`

**Read setup instructions:**
- → `docs/SETUP_GUIDE.md`

**Understand architecture:**
- → `docs/ARCHITECTURE.md`

**Modify database schema:**
- → `database/schema.sql`

**Change face recognition:**
- → `database/face_recognition_db.py`

**Add web features:**
- → `apps/web_app.py` + `web/templates/`

**Fix bugs:**
- → Check `docs/BUG_FIX_ENCOUNTER.md` first

---

## 🗂️ Data Files (Runtime)

Created during operation:
```
face_detection/
├── remind.db                   # SQLite database
├── *.json                      # Config/log files
├── dataset/                    # (legacy) Face samples
├── *.yml                       # (legacy) LBPH models
└── conversation_log_*.json     # Transcription logs
```

**Backup important files:**
```bash
cp remind.db backups/remind_$(date +%Y%m%d).db
```

---

## 🎨 Folder Color Code (for IDE)

Recommended folder colors in your IDE:

- 🔴 **apps/** - Red (critical user-facing code)
- 🔵 **database/** - Blue (core logic)
- 🟢 **web/** - Green (web assets)
- 🟡 **utils/** - Yellow (utilities)
- ⚫ **legacy/** - Gray (deprecated)
- 🟣 **tests/** - Purple (testing)
- 📘 **docs/** - Light blue (documentation)

---

## 📊 Dependency Graph

```
apps/remind_assistant_v2.py
├── database/face_recognition_db.py
│   └── database/person_db.py
├── database/encounter_db.py
└── database/context_extractor.py

apps/web_app.py
├── database/face_recognition_db.py
├── database/person_db.py
└── database/encounter_db.py

apps/quick_enroll.py
└── database/face_recognition_db.py
    └── database/person_db.py
```

---

This organized structure provides:
✅ Clear separation of concerns
✅ Easy navigation
✅ Logical grouping
✅ Scalable architecture
✅ Developer-friendly layout