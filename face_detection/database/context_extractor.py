#!/usr/bin/env python3
"""
Context Extractor for ReMind
Extracts metadata from conversations to learn about people automatically
Uses simple NLP patterns - no heavy dependencies initially
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json


class ContextExtractor:
    """Extract person metadata and context from conversation transcripts"""

    def __init__(self):
        """Initialize context extractor"""
        # Common relationship patterns
        self.relationship_patterns = [
            (r"(?:i'?m|i am) (?:your |the )?(\w+)", "self_intro"),  # "I'm your daughter"
            (r"(?:this is|i'?m) (\w+)", "name_intro"),  # "This is Sarah"
            (r"your (\w+(?:\s+\w+)?)", "relationship"),  # "your daughter", "your home nurse"
        ]

        # Common relationships
        self.known_relationships = {
            'daughter', 'son', 'wife', 'husband', 'sister', 'brother',
            'mother', 'father', 'grandson', 'granddaughter', 'grandchild',
            'nurse', 'doctor', 'caregiver', 'friend', 'neighbor',
            'therapist', 'aide', 'helper'
        }

        # Name introduction patterns
        self.name_patterns = [
            r"(?:my name is|i'?m|this is|call me) (\w+)",
            r"it'?s me,?\s+(\w+)",
            r"(\w+) here",  # "Sarah here"
        ]

        # Time/date patterns
        self.time_patterns = {
            'today': 0,
            'tomorrow': 1,
            'yesterday': -1,
            'monday': None, 'tuesday': None, 'wednesday': None,
            'thursday': None, 'friday': None, 'saturday': None, 'sunday': None,
        }

        # Activity/topic categories
        self.topic_categories = {
            'health': ['doctor', 'medicine', 'pill', 'medication', 'appointment',
                      'hospital', 'pain', 'sick', 'feeling', 'health'],
            'family': ['family', 'child', 'parent', 'grandchild', 'birthday',
                      'visit', 'grandson', 'granddaughter', 'wedding'],
            'daily': ['eat', 'food', 'lunch', 'dinner', 'breakfast', 'sleep',
                     'bath', 'shower', 'walk', 'exercise'],
            'activities': ['tv', 'read', 'book', 'game', 'music', 'church',
                          'shopping', 'park', 'outside'],
        }

    def extract_all(self, transcript: str) -> Dict[str, Any]:
        """
        Extract all metadata from transcript

        Args:
            transcript: Conversation text

        Returns:
            Dictionary with extracted information
        """
        transcript_lower = transcript.lower()

        return {
            'possible_name': self.extract_name(transcript_lower),
            'possible_relationship': self.extract_relationship(transcript_lower),
            'mentioned_dates': self.extract_dates(transcript_lower),
            'mentioned_places': self.extract_places(transcript_lower),
            'action_items': self.extract_action_items(transcript),
            'topics': self.extract_topics(transcript_lower),
            'questions': self.extract_questions(transcript),
            'repetitions': self.detect_repetitions(transcript),
        }

    def extract_name(self, text: str) -> Optional[str]:
        """
        Extract person's name from text

        Args:
            text: Text to analyze (lowercase)

        Returns:
            Extracted name or None
        """
        for pattern in self.name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).capitalize()
                # Filter out common false positives
                if name.lower() not in ['here', 'just', 'back', 'home', 'fine']:
                    return name
        return None

    def extract_relationship(self, text: str) -> Optional[str]:
        """
        Extract relationship from text

        Args:
            text: Text to analyze (lowercase)

        Returns:
            Relationship string or None
        """
        for pattern, pattern_type in self.relationship_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                relationship = match.lower().strip()

                # Check if it's a known relationship
                if relationship in self.known_relationships:
                    return relationship.capitalize()

                # Check for compound relationships
                words = relationship.split()
                if any(word in self.known_relationships for word in words):
                    return relationship.title()

        return None

    def extract_dates(self, text: str) -> List[str]:
        """
        Extract mentioned dates and times

        Args:
            text: Text to analyze

        Returns:
            List of date references
        """
        dates = []

        # Relative dates
        for time_word, offset in self.time_patterns.items():
            if time_word in text:
                if offset is not None:
                    date = datetime.now() + timedelta(days=offset)
                    dates.append(f"{time_word} ({date.strftime('%Y-%m-%d')})")
                else:
                    dates.append(time_word)

        # Specific dates (simple patterns)
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 12/25/2024
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}',  # Dec 25
            r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',  # at 3pm, at 3:30pm
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return list(set(dates))  # Remove duplicates

    def extract_places(self, text: str) -> List[str]:
        """
        Extract mentioned places/locations

        Args:
            text: Text to analyze

        Returns:
            List of places
        """
        places = []

        # Common place patterns
        place_patterns = [
            r'(?:at|to|from) (?:the )?(\w+(?:\s+\w+)?)',  # at the hospital
            r'(?:go|going|went) (?:to )?(?:the )?(\w+)',  # going to the park
        ]

        # Known places
        known_places = [
            'hospital', 'doctor', 'clinic', 'pharmacy', 'store', 'mall',
            'church', 'park', 'restaurant', 'home', 'house', 'kitchen',
            'bedroom', 'bathroom', 'garden', 'library', 'bank'
        ]

        for pattern in place_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if any(place in match.lower() for place in known_places):
                    places.append(match.capitalize())

        return list(set(places))

    def extract_action_items(self, text: str) -> List[Dict[str, str]]:
        """
        Extract things to remember or do

        Args:
            text: Text to analyze

        Returns:
            List of action items with priority
        """
        actions = []

        # Action patterns
        action_patterns = [
            (r"(?:remember to|don'?t forget to|need to|have to|must) (.*?)(?:\.|$)", "high"),
            (r"(?:should|can|might|could) (.*?)(?:\.|$)", "medium"),
            (r"(?:appointment|meeting|visit) .*? (?:on|at) (.*?)(?:\.|$)", "high"),
        ]

        for pattern, priority in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                action = match.strip()
                if len(action) > 5:  # Filter out too short matches
                    actions.append({
                        'action': action,
                        'priority': priority
                    })

        return actions

    def extract_topics(self, text: str) -> Dict[str, List[str]]:
        """
        Extract and categorize conversation topics

        Args:
            text: Text to analyze

        Returns:
            Dictionary of topics by category
        """
        topics = {category: [] for category in self.topic_categories.keys()}

        words = text.lower().split()

        for category, keywords in self.topic_categories.items():
            for keyword in keywords:
                if keyword in words or keyword in text:
                    topics[category].append(keyword)

        # Remove empty categories and duplicates
        return {
            category: list(set(keywords))
            for category, keywords in topics.items()
            if keywords
        }

    def extract_questions(self, text: str) -> List[str]:
        """
        Extract questions asked (useful for detecting confusion)

        Args:
            text: Text to analyze

        Returns:
            List of questions
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        questions = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Check if it's a question
            if '?' in sentence or re.match(r'^\s*(?:who|what|when|where|why|how|is|are|do|does|can|could|would|will)', sentence, re.IGNORECASE):
                questions.append(sentence + '?')

        return questions

    def detect_repetitions(self, text: str) -> Dict[str, Any]:
        """
        Detect repeated questions or phrases (sign of confusion)

        Args:
            text: Text to analyze

        Returns:
            Dictionary with repetition info
        """
        questions = self.extract_questions(text)

        # Simple repetition detection
        question_counts = {}
        for q in questions:
            # Normalize question
            normalized = q.lower().strip('? ')
            question_counts[normalized] = question_counts.get(normalized, 0) + 1

        repeated = {q: count for q, count in question_counts.items() if count > 1}

        return {
            'total_questions': len(questions),
            'unique_questions': len(question_counts),
            'repeated_questions': repeated,
            'repetition_detected': len(repeated) > 0
        }

    def suggest_person_info(self, transcript: str, confidence_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Suggest person information to add to database based on transcript

        Args:
            transcript: Conversation text
            confidence_threshold: Minimum confidence to suggest

        Returns:
            Dictionary with suggested person info or None
        """
        context = self.extract_all(transcript)

        name = context.get('possible_name')
        relationship = context.get('possible_relationship')

        if not name and not relationship:
            return None

        # Calculate confidence based on multiple factors
        confidence_factors = []

        if name:
            # Check if name appears multiple times
            name_count = transcript.lower().count(name.lower())
            confidence_factors.append(min(name_count / 3, 1.0))

        if relationship:
            # Relationship gives higher confidence
            confidence_factors.append(0.8)

        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0

        if confidence < confidence_threshold:
            return None

        return {
            'name': name,
            'relationship': relationship,
            'confidence': confidence,
            'context_clues': {
                'dates_mentioned': context['mentioned_dates'],
                'places_mentioned': context['mentioned_places'],
                'topics_discussed': context['topics'],
                'action_items': context['action_items']
            }
        }

    def generate_encounter_summary(self, transcript: str) -> str:
        """
        Generate a brief summary of the encounter

        Args:
            transcript: Full conversation text

        Returns:
            Summary string
        """
        context = self.extract_all(transcript)

        summary_parts = []

        # Topics
        topics = context['topics']
        if topics:
            main_topics = []
            for category, keywords in topics.items():
                if keywords:
                    main_topics.append(category)
            if main_topics:
                summary_parts.append(f"Discussed: {', '.join(main_topics)}")

        # Action items
        actions = context['action_items']
        if actions:
            high_priority = [a['action'] for a in actions if a['priority'] == 'high']
            if high_priority:
                summary_parts.append(f"Important: {high_priority[0]}")

        # Dates mentioned
        dates = context['mentioned_dates']
        if dates:
            summary_parts.append(f"Mentioned: {dates[0]}")

        return '. '.join(summary_parts) if summary_parts else "Conversation recorded"


# Convenience function
def extract_context(transcript: str) -> Dict[str, Any]:
    """Quick function to extract context from transcript"""
    extractor = ContextExtractor()
    return extractor.extract_all(transcript)


def suggest_new_person(transcript: str) -> Optional[Dict[str, Any]]:
    """Quick function to suggest new person from transcript"""
    extractor = ContextExtractor()
    return extractor.suggest_person_info(transcript)