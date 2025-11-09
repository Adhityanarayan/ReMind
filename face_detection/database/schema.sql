-- ReMind Database Schema for Dementia Assistance
-- SQLite database for storing people, encounters, and conversation metadata

-- People/Contacts Table
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    relationship TEXT,  -- e.g., "Daughter", "Nurse", "Friend", "Doctor"
    photo_path TEXT,
    face_encoding BLOB,  -- Serialized face encoding for recognition
    voice_embedding BLOB,  -- Future: for speaker identification

    -- Contact information
    phone TEXT,
    email TEXT,
    address TEXT,

    -- Metadata
    notes TEXT,  -- Caregiver notes about this person
    important_info TEXT,  -- Critical info (e.g., "Brings medications")

    -- Auto-learned information
    typical_topics TEXT,  -- JSON: Common discussion topics
    visit_frequency TEXT,  -- e.g., "Daily", "Weekly", "Monthly"
    usual_visit_time TEXT,  -- e.g., "Morning", "Afternoon"

    -- Timestamps
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT 1,
    is_trusted BOOLEAN DEFAULT 1  -- For security: trusted people vs strangers
);

-- Encounters/Visits Table
CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,

    -- When and where
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    location TEXT,  -- e.g., "Living Room", "Kitchen", "Outside"

    -- Conversation
    full_transcript TEXT,  -- Complete conversation text
    summary TEXT,  -- AI-generated summary of conversation
    key_topics TEXT,  -- JSON: Extracted topics/keywords

    -- Context extracted from speech
    mentioned_names TEXT,  -- JSON: Other people mentioned
    mentioned_dates TEXT,  -- JSON: Important dates mentioned
    mentioned_places TEXT,  -- JSON: Places mentioned
    action_items TEXT,  -- JSON: Things to remember/do

    -- Sentiment/Health indicators
    patient_mood TEXT,  -- e.g., "Happy", "Confused", "Agitated"
    confusion_level INTEGER,  -- 1-10 scale
    repetitive_questions INTEGER,  -- Count of repeated questions

    -- Recognition confidence
    recognition_confidence FLOAT,  -- How confident was face recognition

    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- Topics/Keywords Table (for trending analysis)
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER,
    topic TEXT NOT NULL,
    category TEXT,  -- e.g., "Health", "Family", "Activities", "Appointments"
    importance INTEGER DEFAULT 1,  -- 1-5 scale
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id) REFERENCES encounters(id)
);

-- Reminders/Important Events
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,  -- Who set this reminder, or NULL for general

    title TEXT NOT NULL,
    description TEXT,
    reminder_type TEXT,  -- "Medication", "Appointment", "Event", "General"

    -- When
    due_date DATE,
    due_time TIME,
    is_recurring BOOLEAN DEFAULT 0,
    recurrence_pattern TEXT,  -- e.g., "Daily", "Weekly Mon/Wed/Fri"

    -- Status
    is_completed BOOLEAN DEFAULT 0,
    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- Conversation Context (for learning from speech)
-- Stores extracted metadata before person is identified
CREATE TABLE IF NOT EXISTS learned_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER,

    -- Extracted information
    possible_name TEXT,  -- e.g., "I'm Sarah" -> "Sarah"
    possible_relationship TEXT,  -- e.g., "your daughter" -> "Daughter"
    context_clues TEXT,  -- JSON: All extracted clues
    confidence FLOAT,  -- How confident we are about this info

    verified BOOLEAN DEFAULT 0,  -- Caregiver confirmed this info

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id) REFERENCES encounters(id)
);

-- Activity Log (for tracking patterns)
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activity_type TEXT,  -- "Visit", "Medication", "Meal", "Exercise", "Confusion"
    description TEXT,
    person_id INTEGER,  -- If related to a person

    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_encounters_person ON encounters(person_id);
CREATE INDEX IF NOT EXISTS idx_encounters_time ON encounters(start_time);
CREATE INDEX IF NOT EXISTS idx_topics_encounter ON topics(encounter_id);
CREATE INDEX IF NOT EXISTS idx_topics_category ON topics(category);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_date, due_time);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp);

-- Views for common queries

-- Recent encounters with person details
CREATE VIEW IF NOT EXISTS recent_encounters AS
SELECT
    e.id,
    e.start_time,
    e.duration_seconds,
    e.summary,
    p.name,
    p.relationship,
    e.key_topics
FROM encounters e
LEFT JOIN people p ON e.person_id = p.id
ORDER BY e.start_time DESC;

-- Person visit frequency
CREATE VIEW IF NOT EXISTS visit_statistics AS
SELECT
    p.id,
    p.name,
    p.relationship,
    COUNT(e.id) as total_visits,
    MAX(e.start_time) as last_visit,
    AVG(e.duration_seconds) as avg_duration_seconds
FROM people p
LEFT JOIN encounters e ON p.id = e.person_id
GROUP BY p.id;