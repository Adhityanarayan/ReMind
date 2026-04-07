#!/usr/bin/env python3
"""
ReMind Browser Web App (Option B)

- Camera + mic captured in the browser via getUserMedia()
- Browser sends snapshots/audio chunks to Flask APIs
- Server does: face recognition + Whisper transcription + DB enrollment

This is intentionally lightweight: no server-side camera/mic capture, no MJPEG streaming.
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import whisper
from flask import Flask, jsonify, make_response, render_template, request
from flask_cors import CORS

from database import EncounterDatabase, FaceRecognitionManager, PersonDatabase, suggest_new_person

app = Flask(__name__)
CORS(app)

# Keep sessions minimal: a client_id cookie + in-memory enrollment buffer.
app.secret_key = os.environ.get("REMIND_SECRET_KEY", "remind-dev-secret")

# System singletons
face_recognition: Optional[FaceRecognitionManager] = None
person_db: Optional[PersonDatabase] = None
encounter_db: Optional[EncounterDatabase] = None
whisper_model = None

# In-memory enrollment state (per client_id)
enroll_state: Dict[str, Dict[str, Any]] = {}

# In-memory transcript state (per client_id)
transcript_state: Dict[str, Dict[str, Any]] = {}

# Whisper is not reliably thread-safe; concurrent /api/transcribe calls can segfault (esp. macOS).
whisper_lock = threading.Lock()


def init_system(db_path: str = "remind.db", whisper_model_name: str = "tiny") -> None:
    global face_recognition, person_db, encounter_db, whisper_model
    face_recognition = FaceRecognitionManager(db_path, tolerance=0.6)
    person_db = PersonDatabase(db_path)
    encounter_db = EncounterDatabase(db_path)
    try:
        import torch

        torch.set_num_threads(1)
    except ImportError:
        pass
    whisper_model = whisper.load_model(whisper_model_name, device="cpu")


def _get_client_id() -> Tuple[str, bool]:
    """Return (client_id, is_new)."""
    cid = request.cookies.get("remind_client_id")
    if cid:
        return cid, False
    return uuid.uuid4().hex, True


def _decode_image_file(file_storage) -> Optional[np.ndarray]:
    """
    Decode uploaded image into BGR frame for OpenCV.
    Accepts jpeg/png/webp (whatever the browser uploads).
    """
    data = file_storage.read()
    if not data:
        return None
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def _person_for_api(person: Dict[str, Any]) -> Dict[str, Any]:
    """Drop binary / numpy fields so jsonify never sees ndarray."""
    out: Dict[str, Any] = {}
    skip = {"face_encoding"}
    for key, val in person.items():
        if key in skip:
            continue
        if isinstance(val, np.ndarray):
            continue
        if isinstance(val, np.floating):
            out[key] = float(val)
        elif isinstance(val, np.integer):
            out[key] = int(val)
        else:
            out[key] = val
    return out


def _suggestion_for_api(suggestion: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not suggestion:
        return None
    return {
        "name": suggestion.get("name"),
        "relationship": suggestion.get("relationship"),
        "confidence": float(suggestion.get("confidence") or 0),
    }


@app.route("/")
def index():
    cid, is_new = _get_client_id()
    resp = make_response(render_template("browser.html"))
    if is_new:
        resp.set_cookie("remind_client_id", cid, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


@app.route("/api/recognize_frame", methods=["POST"])
def recognize_frame():
    """
    POST multipart/form-data:
      - frame: image blob
    Returns person (or unknown) + optional face rectangle.
    """
    assert face_recognition is not None and person_db is not None

    if "frame" not in request.files:
        return jsonify({"success": False, "error": "missing frame file"}), 400

    frame = _decode_image_file(request.files["frame"])
    if frame is None:
        return jsonify({"success": False, "error": "could not decode image"}), 400

    person = face_recognition.recognize_face(frame)
    faces = face_recognition.detect_faces(frame)
    face_rect = None
    if len(faces) > 0:
        # pick largest (x, y, w, h)
        x, y, w, h = max(faces, key=lambda r: int(r[2]) * int(r[3]))
        face_rect = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}

    if person and person.get("id"):
        # refresh details from DB (in case recognition object is a partial dict)
        full = person_db.get_person(int(person["id"]))
        if full:
            full = _person_for_api(dict(full))
            full["match_confidence"] = float(person.get("match_confidence", 0))
            return jsonify({"success": True, "status": "recognized", "person": full, "face": face_rect})

    if face_rect is None:
        return jsonify({"success": True, "status": "no_face"})

    return jsonify({"success": True, "status": "unknown", "face": face_rect})


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """
    POST multipart/form-data:
      - audio: wav blob (recommended: 16kHz mono PCM)
    Returns transcription text.

    Note: Whisper handles resampling internally; WAV keeps it lightweight and avoids codec issues.
    """
    assert whisper_model is not None

    if "audio" not in request.files:
        return jsonify({"success": False, "error": "missing audio file"}), 400

    audio_bytes = request.files["audio"].read()
    if not audio_bytes:
        return jsonify({"success": False, "error": "empty audio file"}), 400

    try:
        # Whisper can transcribe from a file-like object only via temp file path,
        # so we write to an in-memory buffer then to a short-lived temp file.
        # Keep it simple + portable.
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()
            with whisper_lock:
                result = whisper_model.transcribe(
                    f.name,
                    language="en",
                    fp16=False,
                    verbose=False,
                    condition_on_previous_text=False,
                )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    text = (result.get("text") or "").strip()
    ts = datetime.now().isoformat()

    # Store transcript for this client and use it to auto-fill enrollment metadata
    cid, _ = _get_client_id()
    st = transcript_state.setdefault(cid, {"history": [], "full_text": ""})
    if text:
        st["history"].append({"timestamp": ts, "text": text})
        # cap to keep memory bounded
        if len(st["history"]) > 50:
            st["history"] = st["history"][-50:]
        st["full_text"] = (st.get("full_text") or "") + " " + text

    suggestion = None
    enroll = enroll_state.get(cid)
    if text and enroll and enroll.get("active"):
        # Use enrollment-scoped transcript to avoid old noise
        enroll["transcript"] = (enroll.get("transcript") or "") + " " + text
        suggestion = suggest_new_person(enroll["transcript"])

        # Auto-fill fields if we have a reasonably confident suggestion
        if suggestion and float(suggestion.get("confidence") or 0) >= 0.6:
            name = suggestion.get("name")
            relationship = suggestion.get("relationship")

            meta = enroll.get("meta") or {}
            if name and not meta.get("name"):
                meta["name"] = name
            # If user provided a name, do not overwrite it. But if the user left it blank,
            # we allow auto-fill to populate it.
            if name and meta.get("name") in (None, "", "Unknown"):
                meta["name"] = name
            if relationship and not meta.get("relationship"):
                meta["relationship"] = relationship
            enroll["meta"] = meta

    return jsonify(
        {
            "success": True,
            "text": text,
            "timestamp": ts,
            "history": st.get("history", [])[-10:],
            "suggestion": _suggestion_for_api(suggestion),
            "enroll_meta": (enroll.get("meta") if (enroll and enroll.get("active")) else None),
        }
    )


@app.route("/api/enroll/start", methods=["POST"])
def enroll_start():
    """
    JSON body:
      - name (required)
      - relationship/phone/email/important_info/notes (optional)
      - target_samples (default 15)
    """
    cid, _ = _get_client_id()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    # Allow empty name so it can be auto-filled from speech (user asked for this UX).
    # We still require a name at /api/enroll/complete.

    target = int(data.get("target_samples") or 15)
    if target < 10:
        target = 10
    if target > 40:
        target = 40

    enroll_state[cid] = {
        "active": True,
        "ready": False,
        "error": None,
        "target_samples": target,
        "frames": [],  # list[np.ndarray]
        "meta": {
            "name": name or None,
            "relationship": (data.get("relationship") or "").strip() or None,
            "phone": (data.get("phone") or "").strip() or None,
            "email": (data.get("email") or "").strip() or None,
            "important_info": (data.get("important_info") or "").strip() or None,
            "notes": (data.get("notes") or "").strip() or None,
        },
        "started_at": datetime.now().isoformat(),
        "transcript": "",
    }
    return jsonify({"success": True})


@app.route("/api/enroll/add_frame", methods=["POST"])
def enroll_add_frame():
    """
    POST multipart/form-data:
      - frame: image blob
    Adds a frame into the current enrollment buffer (if a face is present).
    """
    assert face_recognition is not None
    cid, _ = _get_client_id()
    st = enroll_state.get(cid)
    if not st or not st.get("active"):
        return jsonify({"success": False, "error": "enrollment not active"}), 400

    if "frame" not in request.files:
        return jsonify({"success": False, "error": "missing frame file"}), 400
    frame = _decode_image_file(request.files["frame"])
    if frame is None:
        return jsonify({"success": False, "error": "could not decode image"}), 400

    # Only collect if a face is detectable (helps avoid bad enrollment)
    faces = face_recognition.detect_faces(frame)
    if len(faces) == 0:
        return jsonify({"success": True, "accepted": False, "reason": "no_face"})

    st["frames"].append(frame)
    if len(st["frames"]) >= int(st["target_samples"]):
        st["ready"] = True

    return jsonify(
        {
            "success": True,
            "accepted": True,
            "samples_captured": len(st["frames"]),
            "target_samples": int(st["target_samples"]),
            "ready": bool(st["ready"]),
        }
    )


@app.route("/api/enroll/status")
def enroll_status():
    cid, _ = _get_client_id()
    st = enroll_state.get(cid)
    if not st:
        return jsonify({"active": False})
    return jsonify(
        {
            "active": bool(st.get("active")),
            "ready": bool(st.get("ready")),
            "error": st.get("error"),
            "samples_captured": len(st.get("frames") or []),
            "target_samples": int(st.get("target_samples") or 0),
            "meta": st.get("meta"),
            "started_at": st.get("started_at"),
        }
    )


@app.route("/api/enroll/cancel", methods=["POST"])
def enroll_cancel():
    cid, _ = _get_client_id()
    enroll_state.pop(cid, None)
    return jsonify({"success": True})


@app.route("/api/enroll/complete", methods=["POST"])
def enroll_complete():
    assert face_recognition is not None
    cid, _ = _get_client_id()
    st = enroll_state.get(cid)
    if not st or not st.get("active"):
        return jsonify({"success": False, "error": "enrollment not active"}), 400

    frames: List[np.ndarray] = list(st.get("frames") or [])
    if len(frames) < 10:
        return jsonify({"success": False, "error": "need at least 10 samples"}), 400

    meta = st.get("meta") or {}
    if not (meta.get("name") or "").strip():
        return jsonify({"success": False, "error": "name is required (say 'my name is ...' or type it)"}), 400
    try:
        person_id = face_recognition.enroll_person(frames=frames, **meta)
    except Exception as e:
        st["error"] = str(e)
        return jsonify({"success": False, "error": str(e)}), 500

    enroll_state.pop(cid, None)
    return jsonify({"success": True, "person_id": person_id})


def run(host: str = "0.0.0.0", port: int = 5002, db_path: str = "remind.db", model: str = "tiny") -> None:
    init_system(db_path=db_path, whisper_model_name=model)
    print(f"\n🌐 Starting ReMind Browser Web App on http://{host}:{port}")
    print("   This uses browser camera+mic (getUserMedia).")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ReMind Browser Web App (camera+mic in browser)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5002)
    parser.add_argument("--db", default="remind.db")
    parser.add_argument("--model", default="tiny", choices=["tiny", "base", "small"])
    args = parser.parse_args()

    run(args.host, args.port, args.db, args.model)

