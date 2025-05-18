#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prosody formatter for the VANTA Voice Pipeline.

Provides text formatting and SSML generation capabilities to enhance
the naturalness and expressiveness of text-to-speech synthesis.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-004-003 - Implement natural conversational features

import re
import logging
from typing import List, Dict, Any, Optional
import xml.sax.saxutils as saxutils

logger = logging.getLogger(__name__)

class ProsodyFormatter:
    """
    Text formatting and prosody control for TTS.
    
    Provides utilities for preparing text for speech synthesis,
    including punctuation normalization, number expansion, and
    SSML generation for improved prosody.
    """
    
    def __init__(self,
                 add_punctuation: bool = True,
                 enhance_questions: bool = True,
                 enhance_emphasis: bool = True,
                 normalize_numbers: bool = True,
                 expand_abbreviations: bool = True):
        """
        Initialize prosody formatter.
        
        Args:
            add_punctuation: Whether to ensure text has proper punctuation
            enhance_questions: Whether to enhance question intonation
            enhance_emphasis: Whether to add emphasis to important words
            normalize_numbers: Whether to convert numbers to speakable form
            expand_abbreviations: Whether to expand common abbreviations
        """
        self.add_punctuation = add_punctuation
        self.enhance_questions = enhance_questions
        self.enhance_emphasis = enhance_emphasis
        self.normalize_numbers = normalize_numbers
        self.expand_abbreviations = expand_abbreviations
        
        # Common abbreviations and their expansions
        self.abbreviations = {
            "Mr.": "Mister",
            "Mrs.": "Misses",
            "Dr.": "Doctor",
            "Prof.": "Professor",
            "St.": "Street",
            "Apt.": "Apartment",
            "vs.": "versus",
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "etcetera",
            "fig.": "figure",
        }
        
        # Emphasis words (commonly emphasized in speech)
        self.emphasis_words = [
            "must", "very", "extremely", "absolutely", "definitely",
            "never", "always", "critical", "important", "urgent",
            "immediately", "vital", "essential", "crucial"
        ]
        
        # Emotion patterns for detection
        self.emotion_patterns = {
            "happy": ["happy", "great", "excellent", "awesome", "exciting", "wonderful", "joy"],
            "sad": ["sad", "sorry", "unfortunate", "regret", "apologize", "unhappy"],
            "urgent": ["urgent", "emergency", "immediately", "danger", "critical", "hurry"],
            "calm": ["relax", "calm", "peaceful", "gently", "carefully"]
        }
    
    def format_text(self, text: str) -> str:
        """
        Format plain text for better synthesis.
        
        Args:
            text: Text to format
            
        Returns:
            Formatted text
        """
        formatted_text = text
        
        # Apply formatting steps based on configuration
        if self.expand_abbreviations:
            formatted_text = self.expand_abbreviations_in_text(formatted_text)
            
        if self.normalize_numbers:
            formatted_text = self.normalize_numbers_in_text(formatted_text)
            
        if self.add_punctuation:
            formatted_text = self.ensure_punctuation(formatted_text)
            
        return formatted_text
    
    def expand_abbreviations_in_text(self, text: str) -> str:
        """
        Expand common abbreviations.
        
        Args:
            text: Text containing abbreviations
            
        Returns:
            Text with expanded abbreviations
        """
        result = text
        for abbr, expansion in self.abbreviations.items():
            # Use word boundary to match whole abbreviations
            pattern = r'\b' + re.escape(abbr) + r'\b'
            result = re.sub(pattern, expansion, result)
        return result
    
    def normalize_numbers_in_text(self, text: str) -> str:
        """
        Convert numbers to speakable form.
        
        Args:
            text: Text containing numbers
            
        Returns:
            Text with normalized numbers
        """
        # Handle percentages
        text = re.sub(r'(\d+)%', r'\1 percent', text)
        
        # Handle currencies
        text = re.sub(r'\$(\d+)', r'\1 dollars', text)
        text = re.sub(r'\$(\d+)\.(\d{2})', r'\1 dollars and \2 cents', text)
        
        # Handle time
        text = re.sub(r'(\d+):(\d{2})( [AP]M)', r'\1 \2\3', text)
        text = re.sub(r'(\d+):(\d{2})', r'\1 \2', text)
        
        # Handle large numbers by removing commas
        text = re.sub(r'(\d{1,3}),(\d{3})(,\d{3})*', r'\1\2\3', text)
        
        # Convert ordinals
        text = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1 \2', text)
        
        # Convert ranges
        text = re.sub(r'(\d+)-(\d+)', r'\1 to \2', text)
        
        return text
    
    def ensure_punctuation(self, text: str) -> str:
        """
        Ensure text has proper end punctuation.
        
        Args:
            text: Text to check/modify
            
        Returns:
            Text with proper end punctuation
        """
        text = text.strip()
        if not text:
            return text
            
        # Add period if no end punctuation
        if not text[-1] in ['.', '!', '?', ':', ';']:
            text += '.'
            
        return text
    
    def to_ssml(self, text: str, 
               speaking_rate: float = 1.0,
               pitch: float = 0.0,
               emphasis_words: Optional[List[str]] = None) -> str:
        """
        Convert plain text to SSML markup.
        
        Args:
            text: Text to convert
            speaking_rate: Overall speaking rate
            pitch: Overall pitch adjustment
            emphasis_words: Words to emphasize
            
        Returns:
            SSML markup
        """
        # First, escape special characters
        escaped_text = saxutils.escape(text)
        
        # Format the text
        formatted_text = self.format_text(escaped_text)
        
        # Detect dominant emotion
        emotion = self.detect_emotion(formatted_text)
        
        # Build SSML document
        ssml = f"""<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis">
  <prosody rate="{speaking_rate}" pitch="{pitch}st">
"""
        
        # Add emphasis to important words
        if self.enhance_emphasis:
            words_to_emphasize = emphasis_words or self.emphasis_words
            for word in words_to_emphasize:
                pattern = r'\b' + re.escape(word) + r'\b'
                formatted_text = re.sub(
                    pattern, 
                    f'<emphasis level="moderate">{word}</emphasis>', 
                    formatted_text
                )
                
        # Add processing for questions
        if self.enhance_questions and '?' in formatted_text:
            sentences = re.split(r'([.!?])', formatted_text)
            processed_text = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i] if i < len(sentences) else ""
                punctuation = sentences[i+1] if i+1 < len(sentences) else ""
                
                if punctuation == '?':
                    # Questions typically have rising intonation
                    processed_text += f'<prosody rate="0.95" pitch="+1st">{sentence}{punctuation}</prosody> '
                else:
                    processed_text += sentence + punctuation + ' '
                    
            formatted_text = processed_text.strip()
            
        # Add the formatted text to SSML
        ssml += f"    {formatted_text}\n"
        ssml += "  </prosody>\n"
        ssml += "</speak>"
        
        # Add emotion-specific adjustments
        ssml = self.add_prosody_for_emotion(ssml, emotion)
        
        return ssml
    
    def detect_emotion(self, text: str) -> str:
        """
        Detect emotional tone of text for appropriate prosody.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected emotion (happy, sad, urgent, calm, or neutral)
        """
        text_lower = text.lower()
        
        # Count matches for each emotion
        emotion_counts = {}
        for emotion, patterns in self.emotion_patterns.items():
            count = sum(1 for pattern in patterns if pattern in text_lower)
            emotion_counts[emotion] = count
        
        # Find emotion with highest count
        if emotion_counts:
            max_emotion = max(emotion_counts.items(), key=lambda x: x[1])
            if max_emotion[1] > 0:
                return max_emotion[0]
        
        return "neutral"
    
    def add_prosody_for_emotion(self, ssml: str, emotion: str) -> str:
        """
        Add emotion-specific prosody to SSML.
        
        Args:
            ssml: SSML markup
            emotion: Detected emotion
            
        Returns:
            SSML with emotion-specific prosody
        """
        if emotion == "happy":
            # Happy: slightly faster, higher pitch
            return ssml.replace('<prosody rate=', '<prosody pitch="+1st" rate=')
        elif emotion == "sad":
            # Sad: slower, lower pitch
            return ssml.replace('<prosody rate=', '<prosody pitch="-1st" rate="0.95" ')
        elif emotion == "urgent":
            # Urgent: faster, louder
            return ssml.replace('<prosody rate=', '<prosody rate="1.1" volume="+2dB" ')
        elif emotion == "calm":
            # Calm: slower, softer
            return ssml.replace('<prosody rate=', '<prosody rate="0.9" volume="-1dB" pitch="-0.5st" ')
        else:
            # Neutral: no changes
            return ssml
    
    def add_hesitations(self, text: str, frequency: float = 0.1) -> str:
        """
        Add natural hesitations to make speech sound more human.
        
        Args:
            text: Text to modify
            frequency: Frequency of hesitations (0.0-1.0)
            
        Returns:
            Text with hesitations
        """
        # Split text into sentences
        sentences = re.split(r'([.!?])', text)
        result = ""
        
        import random
        random.seed(hash(text))  # Deterministic randomness
        
        hesitations = ["um", "uh", "hmm", "er"]
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] if i < len(sentences) else ""
            punctuation = sentences[i+1] if i+1 < len(sentences) else ""
            
            # Add hesitation at start of some longer sentences
            if len(sentence) > 40 and random.random() < frequency:
                hesitation = random.choice(hesitations)
                sentence = f"{hesitation}, {sentence}"
                
            # Add hesitation after commas sometimes
            if "," in sentence and random.random() < frequency:
                comma_splits = sentence.split(",", 1)
                hesitation = random.choice(hesitations)
                sentence = f"{comma_splits[0]}, {hesitation},{comma_splits[1]}"
                
            result += sentence + punctuation + " "
            
        return result.strip()
    
    def add_natural_pauses(self, text: str) -> str:
        """
        Add explicit pause markers for more natural speech rhythm.
        
        Args:
            text: Text to modify
            
        Returns:
            Text with pause markers
        """
        # Add pauses after punctuation
        text = re.sub(r'([.!?])\s+', r'\1 <break time="0.8s"/> ', text)
        text = re.sub(r'([;:])\s+', r'\1 <break time="0.5s"/> ', text)
        text = re.sub(r'([,])\s+', r'\1 <break time="0.3s"/> ', text)
        
        # Add pauses for parenthetical phrases
        text = re.sub(r'\((.*?)\)', r'<break time="0.2s"/> (\1) <break time="0.2s"/>', text)
        
        # Add pauses for dashes
        text = re.sub(r'\s+--\s+', r' <break time="0.4s"/> -- <break time="0.2s"/> ', text)
        
        return text