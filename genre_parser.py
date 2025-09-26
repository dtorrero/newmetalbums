#!/usr/bin/env python3
"""
Genre Parser for Metal Albums
Handles parsing and classification of complex genre strings from Metal Archives

TODO: FUTURE IMPROVEMENTS - AI-POWERED GENRE CLASSIFICATION
=============================================================
The current implementation uses simple pattern matching and heuristics, which achieves
~70-80% accuracy but has limitations:

CURRENT LIMITATIONS:
- False positives: "Heavy Rain", "Death Valley" classified as metal
- False negatives: "Djent", "Shoegaze" might be missed
- No semantic understanding or context awareness
- Simple string matching without meaning comprehension

PROPOSED AI IMPROVEMENTS:
1. **Text Classification Model**: Train a transformer model (BERT/RoBERTa) on Metal Archives data
   - Input: Raw genre string
   - Output: Genre category, confidence, modifiers
   - Training data: Thousands of Metal Archives genre strings with manual labels

2. **Embedding-Based Similarity**: Use sentence embeddings to find similar genres
   - Pre-trained models: sentence-transformers, all-MiniLM-L6-v2
   - Build genre embeddings database for similarity matching
   - Handle typos and variations automatically

3. **Multi-Modal Approach**: Combine multiple signals
   - Text patterns (current approach)
   - Semantic embeddings
   - Music knowledge graphs
   - User feedback for continuous learning

4. **Implementation Options**:
   - Local models: sentence-transformers, spaCy NER
   - Cloud APIs: OpenAI GPT, Google Cloud NLP
   - Hybrid: Pattern matching + AI fallback

ESTIMATED ACCURACY IMPROVEMENT: 70-80% → 90-95%
IMPLEMENTATION EFFORT: 2-3 days for basic model, 1-2 weeks for advanced system
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ParsedGenre:
    """Represents a parsed genre with metadata"""
    main: str                    # Primary genre: "Black Metal"
    modifiers: List[str]         # Modifiers: ["Atmospheric", "Melodic"]
    related: List[str]           # Related genres: ["Post-Rock", "Doom Metal"]
    period: Optional[str] = None # Temporal qualifier: "early", "mid", "later"
    confidence: float = 1.0      # Parsing confidence score (0-1)

class GenreParser:
    """Intelligent parser for complex Metal Archives genre strings"""
    
    def __init__(self):
        # Primary separators for genre strings
        self.separators = ['/', ',', ';']
        
        # Temporal patterns to extract period information
        self.temporal_patterns = [
            r'\(early\)', r'\(mid\)', r'\(middle\)', r'\(later\)', 
            r'\(late\)', r'\(now\)', r'\(current\)', r'\(recent\)'
        ]
        
        # Dynamic pattern recognition - no hardcoded genre lists!
        
        # Metal indicators (words that suggest metal genres)
        self.metal_indicators = {
            'metal', 'core', 'grind', 'doom', 'black', 'death', 'thrash', 
            'heavy', 'power', 'speed', 'sludge', 'stoner', 'drone'
        }
        
        # Common modifiers (descriptive words that modify genres)
        self.modifier_patterns = {
            'atmospheric', 'melodic', 'progressive', 'symphonic', 'technical',
            'brutal', 'raw', 'ambient', 'experimental', 'industrial',
            'epic', 'aggressive', 'dark', 'blackened', 'old school',
            'modern', 'traditional', 'avant-garde', 'psychedelic',
            'post', 'neo', 'proto', 'retro', 'depressive', 'funeral',
            'viking', 'pagan', 'folk', 'gothic', 'nu'
        }
        
        # Non-metal genre indicators (for related genres)
        self.non_metal_indicators = {
            'rock', 'punk', 'hardcore', 'jazz', 'classical', 'electronic',
            'ambient', 'folk', 'blues', 'country', 'noise', 'shoegaze',
            'emo', 'indie', 'alternative', 'experimental'
        }
        
        # Common genre aliases and normalizations
        self.genre_aliases = {
            'BM': 'Black Metal',
            'DM': 'Death Metal',
            'TM': 'Thrash Metal',
            'HM': 'Heavy Metal',
            'PM': 'Power Metal',
            'Blackened Death Metal': 'Black/Death Metal',
            'Death/Black Metal': 'Black/Death Metal',
            'Thrash/Death Metal': 'Death/Thrash Metal',
            'Melodic Death Metal': 'Melodic Death Metal',
            'Technical Death Metal': 'Technical Death Metal',
            'Brutal Death Metal': 'Brutal Death Metal'
        }
        
        # Confidence scoring weights
        self.confidence_weights = {
            'exact_match': 1.0,
            'partial_match': 0.8,
            'inferred_match': 0.6,
            'uncertain_match': 0.4
        }
    
    def parse_genre_string(self, genre_string: str) -> List[ParsedGenre]:
        """
        Parse complex genre string into structured ParsedGenre objects
        
        Args:
            genre_string: Raw genre string from Metal Archives
            
        Returns:
            List of ParsedGenre objects with parsed information
        """
        if not genre_string or genre_string.strip() == '':
            return []
        
        logger.debug(f"Parsing genre string: '{genre_string}'")
        
        # Step 1: Extract temporal information
        clean_string, temporal_info = self.extract_temporal_info(genre_string)
        
        # Step 2: Split by main separators and process each segment
        segments = self._split_genre_segments(clean_string)
        
        # Step 3: Parse each segment into structured data
        parsed_genres = []
        for segment in segments:
            parsed = self._parse_single_segment(segment.strip(), temporal_info)
            if parsed:
                parsed_genres.extend(parsed)
        
        # Step 4: Post-process and deduplicate
        parsed_genres = self._deduplicate_genres(parsed_genres)
        
        logger.debug(f"Parsed {len(parsed_genres)} genres from '{genre_string}'")
        return parsed_genres
    
    def normalize_genre(self, genre: str) -> str:
        """
        Normalize genre names for consistency
        
        Args:
            genre: Raw genre name
            
        Returns:
            Normalized genre name
        """
        if not genre:
            return ""
        
        # Remove extra whitespace and normalize case
        normalized = ' '.join(genre.strip().split())
        
        # Apply aliases
        if normalized in self.genre_aliases:
            normalized = self.genre_aliases[normalized]
        
        # Ensure proper capitalization
        normalized = self._capitalize_genre(normalized)
        
        return normalized
    
    def extract_temporal_info(self, genre_string: str) -> Tuple[str, Dict[str, str]]:
        """
        Extract temporal qualifiers from genre string
        
        Args:
            genre_string: Raw genre string
            
        Returns:
            Tuple of (cleaned_string, temporal_info_dict)
        """
        temporal_info = {}
        clean_string = genre_string
        
        # Find all temporal patterns
        for pattern in self.temporal_patterns:
            matches = re.finditer(pattern, genre_string, re.IGNORECASE)
            for match in matches:
                period = match.group().strip('()')
                # Find the genre segment this period applies to
                start_pos = max(0, match.start() - 50)  # Look back 50 chars
                segment = genre_string[start_pos:match.start()].strip()
                
                # Extract the last genre mentioned before the period
                genre_parts = re.split(r'[/,;]', segment)
                if genre_parts:
                    last_genre = genre_parts[-1].strip()
                    if last_genre:
                        temporal_info[last_genre] = period.lower()
                
                # Remove the temporal pattern from the string
                clean_string = clean_string.replace(match.group(), '')
        
        return clean_string.strip(), temporal_info
    
    def build_genre_hierarchy(self, genres: List[str]) -> Dict[str, List[str]]:
        """
        Dynamically build parent-child relationships between genres
        
        Args:
            genres: List of genre names
            
        Returns:
            Dictionary mapping parent genres to child genres
        """
        hierarchy = {}
        
        for genre in genres:
            parent = self._find_parent_genre_dynamic(genre)
            if parent and parent != genre:
                if parent not in hierarchy:
                    hierarchy[parent] = []
                if genre not in hierarchy[parent]:
                    hierarchy[parent].append(genre)
        
        return hierarchy
    
    def _find_parent_genre_dynamic(self, genre: str) -> Optional[str]:
        """Dynamically find parent genre based on linguistic patterns"""
        words = genre.lower().split()
        
        # If it's a compound genre, try to find the base
        if len(words) > 1:
            # Check if it ends with a metal type (last 1-2 words)
            for i in range(1, min(3, len(words) + 1)):
                potential_base = ' '.join(words[-i:])
                
                # If the potential base contains metal indicators, it might be the parent
                if any(indicator in potential_base for indicator in self.metal_indicators):
                    # The parent would be this base genre
                    base_genre = ' '.join(word.title() for word in potential_base.split())
                    if base_genre != genre:  # Don't make it its own parent
                        return base_genre
        
        return None
    
    def get_parsing_statistics(self, genre_strings: List[str]) -> Dict[str, any]:
        """
        Generate parsing statistics for a collection of genre strings
        
        Args:
            genre_strings: List of raw genre strings
            
        Returns:
            Dictionary with parsing statistics
        """
        stats = {
            'total_strings': len(genre_strings),
            'successfully_parsed': 0,
            'parsing_errors': 0,
            'average_confidence': 0.0,
            'genre_frequency': Counter(),
            'modifier_frequency': Counter(),
            'temporal_usage': Counter(),
            'unparsed_strings': []
        }
        
        total_confidence = 0.0
        
        for genre_string in genre_strings:
            try:
                parsed = self.parse_genre_string(genre_string)
                if parsed:
                    stats['successfully_parsed'] += 1
                    for genre in parsed:
                        stats['genre_frequency'][genre.main] += 1
                        stats['modifier_frequency'].update(genre.modifiers)
                        if genre.period:
                            stats['temporal_usage'][genre.period] += 1
                        total_confidence += genre.confidence
                else:
                    stats['unparsed_strings'].append(genre_string)
            except Exception as e:
                stats['parsing_errors'] += 1
                stats['unparsed_strings'].append(genre_string)
                logger.warning(f"Error parsing '{genre_string}': {e}")
        
        if stats['successfully_parsed'] > 0:
            stats['average_confidence'] = total_confidence / stats['successfully_parsed']
        
        return stats
    
    def _split_genre_segments(self, genre_string: str) -> List[str]:
        """Split genre string into segments using separators"""
        # Handle semicolon first (strongest separator for temporal changes)
        if ';' in genre_string:
            segments = genre_string.split(';')
        else:
            # Split by comma or slash
            segments = re.split(r'[,/]', genre_string)
        
        return [seg.strip() for seg in segments if seg.strip()]
    
    def _parse_single_segment(self, segment: str, temporal_info: Dict[str, str]) -> List[ParsedGenre]:
        """Parse a single genre segment into ParsedGenre objects"""
        parsed_genres = []
        
        # Normalize the segment
        normalized_segment = self.normalize_genre(segment)
        
        # Check if it's a compound genre (contains '/')
        if '/' in normalized_segment:
            # Split compound genres
            parts = [p.strip() for p in normalized_segment.split('/')]
            for part in parts:
                parsed = self._identify_genre_components(part, temporal_info)
                if parsed:
                    parsed_genres.append(parsed)
        else:
            # Single genre
            parsed = self._identify_genre_components(normalized_segment, temporal_info)
            if parsed:
                parsed_genres.append(parsed)
        
        return parsed_genres
    
    def _identify_genre_components(self, genre: str, temporal_info: Dict[str, str]) -> Optional[ParsedGenre]:
        """Dynamically identify main genre, modifiers, and related genres from any genre string"""
        if not genre:
            return None
        
        # FUTURE: Try AI model first (when implemented)
        ai_result = self._classify_with_ai_model(genre)
        if ai_result:
            # AI model provided a result, use it
            ai_result.period = temporal_info.get(genre)
            return ai_result
        
        # Fall back to pattern matching (current implementation)
        main_genre = ""
        modifiers = []
        related = []
        confidence = 1.0
        period = temporal_info.get(genre)
        
        # Normalize for analysis (but keep original for output)
        words = [word.strip() for word in genre.split()]
        words_lower = [word.lower() for word in words]
        
        # Dynamic genre type detection
        is_metal = self._is_metal_genre(words_lower)
        detected_modifiers = self._extract_modifiers(words_lower)
        
        if is_metal:
            # This is a metal genre
            main_genre = genre
            modifiers = detected_modifiers
            confidence = self._calculate_confidence(genre, is_metal, detected_modifiers)
        else:
            # Check if it's a non-metal related genre
            is_related = self._is_related_genre(words_lower)
            if is_related:
                related.append(genre)
                confidence = 0.8
            else:
                # Unknown genre - treat as main genre with lower confidence
                main_genre = genre
                confidence = 0.5
        
        # If we couldn't identify anything meaningful, skip
        if not main_genre and not related:
            return None
        
        return ParsedGenre(
            main=main_genre,
            modifiers=modifiers,
            related=related,
            period=period,
            confidence=confidence
        )
    
    def _is_metal_genre(self, words_lower: List[str]) -> bool:
        """Dynamically determine if a genre is metal-related"""
        # Check for explicit metal indicators
        for word in words_lower:
            if any(indicator in word for indicator in self.metal_indicators):
                return True
        
        # Check for metal-specific patterns
        genre_text = ' '.join(words_lower)
        
        # Ends with 'metal' or 'core'
        if genre_text.endswith('metal') or genre_text.endswith('core'):
            return True
        
        # Contains metal subgenre patterns
        metal_patterns = ['black', 'death', 'thrash', 'doom', 'heavy', 'power', 'speed']
        if any(pattern in genre_text for pattern in metal_patterns):
            return True
        
        # Contains 'grind' (grindcore, etc.)
        if 'grind' in genre_text:
            return True
        
        return False
    
    def _is_related_genre(self, words_lower: List[str]) -> bool:
        """Determine if a genre is a related non-metal genre"""
        genre_text = ' '.join(words_lower)
        
        # Check for non-metal indicators
        for indicator in self.non_metal_indicators:
            if indicator in genre_text:
                return True
        
        return False
    
    def _extract_modifiers(self, words_lower: List[str]) -> List[str]:
        """Extract modifier words from the genre"""
        modifiers = []
        
        for word in words_lower:
            # Check if word is a known modifier pattern
            if word in self.modifier_patterns:
                modifiers.append(word.title())  # Capitalize for output
            # Check for compound modifiers like "old school"
            elif word == 'old' and 'school' in words_lower:
                modifiers.append('Old School')
        
        # Handle multi-word modifiers
        genre_text = ' '.join(words_lower)
        multi_word_modifiers = ['old school', 'avant-garde']
        for modifier in multi_word_modifiers:
            if modifier in genre_text and modifier.title() not in modifiers:
                modifiers.append(modifier.title())
        
        return list(set(modifiers))  # Remove duplicates
    
    def _calculate_confidence(self, genre: str, is_metal: bool, modifiers: List[str]) -> float:
        """Calculate confidence score based on genre characteristics"""
        confidence = 0.5  # Base confidence
        
        words_lower = [word.lower() for word in genre.split()]
        
        # Higher confidence for clear metal genres
        if is_metal:
            confidence += 0.3
            
            # Even higher for explicit metal indicators
            if any('metal' in word for word in words_lower):
                confidence += 0.2
        
        # Boost confidence for recognized modifiers
        if modifiers:
            confidence += len(modifiers) * 0.1
        
        # Boost confidence for common patterns
        common_patterns = ['black metal', 'death metal', 'thrash metal', 'heavy metal']
        if any(pattern in genre.lower() for pattern in common_patterns):
            confidence += 0.2
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _classify_with_ai_model(self, genre: str) -> Optional[ParsedGenre]:
        """
        FUTURE: AI-powered genre classification
        
        This method is a placeholder for future AI model integration.
        When implemented, it should:
        1. Use a trained transformer model for genre classification
        2. Return ParsedGenre with higher accuracy than pattern matching
        3. Handle edge cases and ambiguous genres better
        
        Args:
            genre: Raw genre string
            
        Returns:
            ParsedGenre object with AI-predicted classification
            
        Implementation ideas:
        - sentence-transformers for semantic similarity
        - Fine-tuned BERT model on Metal Archives data
        - OpenAI API for complex genre analysis
        - Hybrid approach: AI + pattern matching
        """
        # TODO: Implement AI model integration
        # For now, return None to fall back to pattern matching
        return None
    
    def _deduplicate_genres(self, genres: List[ParsedGenre]) -> List[ParsedGenre]:
        """Remove duplicate genres and merge similar ones"""
        if not genres:
            return []
        
        # Group by main genre
        genre_groups = {}
        for genre in genres:
            key = genre.main
            if key not in genre_groups:
                genre_groups[key] = []
            genre_groups[key].append(genre)
        
        # Merge duplicates within each group
        deduplicated = []
        for main_genre, group in genre_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Merge multiple instances of the same main genre
                merged = self._merge_genre_instances(group)
                deduplicated.append(merged)
        
        return deduplicated
    
    def _merge_genre_instances(self, genres: List[ParsedGenre]) -> ParsedGenre:
        """Merge multiple instances of the same main genre"""
        if len(genres) == 1:
            return genres[0]
        
        # Take the first as base
        merged = genres[0]
        
        # Combine modifiers and related genres
        all_modifiers = set(merged.modifiers)
        all_related = set(merged.related)
        total_confidence = merged.confidence
        
        for genre in genres[1:]:
            all_modifiers.update(genre.modifiers)
            all_related.update(genre.related)
            total_confidence += genre.confidence
            
            # Use the most specific period if available
            if genre.period and not merged.period:
                merged.period = genre.period
        
        # Average confidence
        merged.confidence = total_confidence / len(genres)
        merged.modifiers = sorted(list(all_modifiers))
        merged.related = sorted(list(all_related))
        
        return merged
    
    def _capitalize_genre(self, genre: str) -> str:
        """Properly capitalize genre names"""
        # Special cases for metal genres
        special_cases = {
            'metal': 'Metal',
            'black': 'Black',
            'death': 'Death',
            'thrash': 'Thrash',
            'heavy': 'Heavy',
            'doom': 'Doom',
            'power': 'Power',
            'folk': 'Folk',
            'progressive': 'Progressive',
            'symphonic': 'Symphonic',
            'gothic': 'Gothic',
            'industrial': 'Industrial',
            'post': 'Post',
            'rock': 'Rock',
            'hardcore': 'Hardcore',
            'punk': 'Punk'
        }
        
        words = genre.split()
        capitalized_words = []
        
        for word in words:
            lower_word = word.lower()
            if lower_word in special_cases:
                capitalized_words.append(special_cases[lower_word])
            else:
                capitalized_words.append(word.capitalize())
        
        return ' '.join(capitalized_words)


# Example usage and testing
if __name__ == "__main__":
    parser = GenreParser()
    
    # Test cases from the plan
    test_cases = [
        "Black Metal",
        "Black Metal/Post-Rock",
        "Black Metal, Black/Thrash Metal",
        "Progressive/Melodic Death/Black Metal",
        "Doom/Death Metal (early); Progressive Death/Black Metal (mid)",
        "Black 'n' Roll/D-Beat",
        "Atmospheric Black Metal",
        "Technical Death Metal/Progressive Metal"
    ]
    
    print("Genre Parser Test Results:")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\nInput: '{test_case}'")
        parsed = parser.parse_genre_string(test_case)
        for i, genre in enumerate(parsed, 1):
            print(f"  {i}. Main: {genre.main}")
            if genre.modifiers:
                print(f"     Modifiers: {', '.join(genre.modifiers)}")
            if genre.related:
                print(f"     Related: {', '.join(genre.related)}")
            if genre.period:
                print(f"     Period: {genre.period}")
            print(f"     Confidence: {genre.confidence:.2f}")
    
    # Generate statistics
    stats = parser.get_parsing_statistics(test_cases)
    print(f"\nParsing Statistics:")
    print(f"Successfully parsed: {stats['successfully_parsed']}/{stats['total_strings']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"Most common genres: {dict(stats['genre_frequency'].most_common(5))}")
