"""
ReMind Database Package
Database modules for person management, encounter logging, and context extraction
"""

from .person_db import PersonDatabase, create_person, get_person, find_by_name
from .encounter_db import EncounterDatabase
from .context_extractor import ContextExtractor, extract_context, suggest_new_person
from .face_recognition_db import FaceRecognitionManager
from .opencv_face_recognition import OpenCVFaceRecognizer

__all__ = [
    'PersonDatabase',
    'EncounterDatabase',
    'ContextExtractor',
    'FaceRecognitionManager',
    'OpenCVFaceRecognizer',
    'create_person',
    'get_person',
    'find_by_name',
    'extract_context',
    'suggest_new_person',
]