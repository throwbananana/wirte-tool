from abc import ABC, abstractmethod
import re
from datetime import datetime

class AnalysisUtils:
    @staticmethod
    def extract_characters(text, known_characters):
        """
        Extract character names from text based on format 【Name】
        and filter against a list of known characters.
        """
        if not text: return []
        matches = re.findall(r"【(.*?)】", text)
        if not matches: return []
        
        valid_chars = {c["name"] for c in known_characters}
        return list(set(matches).intersection(valid_chars))

    @staticmethod
    def parse_date(date_str):
        """
        Parse date from string. Support YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD, 
        and relative formats like 'Day 1', '第1天'.
        Return formatted string YYYY-MM-DD or None for relative dates (returns raw string if it looks like time).
        """
        if not date_str: return None
        date_str = date_str.strip()
        
        # Standard Date
        match = re.search(r"(\d{4})[-/年\.](\d{1,2})[-/月\.](\d{1,2})", date_str)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            
        # Relative Day (Day X, 第X天) -> We can't convert to Date without start date, 
        # so we return a standardized relative string or just pass it through if it looks like a valid time marker.
        # But for Timeline view which expects date positions, this is tricky.
        # Let's just return standardized string for now.
        
        if re.match(r"(Day|day)\s*\d+", date_str) or re.match(r"第\s*\d+\s*天", date_str):
            return date_str # Return as is, Timeline might handle it as label
            
        return None

    @staticmethod
    def check_clue_status(clue_name, all_script_text):
        """
        Analyze clue usage in script.
        Returns: "unused" (0), "mentioned" (1-2), "resolved" (3+ or spread out)
        """
        if not clue_name or not all_script_text:
            return "unused"

        count = all_script_text.count(clue_name)
        if count == 0:
            return "unused"
        elif count < 3:
            return "mentioned"
        else:
            return "resolved"

    @staticmethod
    def parse_datetime(date_str):
        """
        Parse datetime from string. Supports multiple formats:
        - YYYY-MM-DD HH:MM
        - YYYY-MM-DD
        - YYYY.MM.DD
        - YYYY/MM/DD
        - YYYY年MM月DD日

        Returns: datetime object or None if unparseable
        """
        if not date_str:
            return None
        date_str = date_str.strip()

        # Try YYYY-MM-DD HH:MM format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # Try YYYY-MM-DD format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

        # Try other formats with regex
        match = re.search(r"(\d{4})[-/年\.](\d{1,2})[-/月\.](\d{1,2})", date_str)
        if match:
            try:
                y, m, d = match.groups()
                return datetime(int(y), int(m), int(d))
            except ValueError:
                pass

        return None

    @staticmethod
    def get_sort_key_for_event(event):
        """
        Get a sortable key for timeline events.
        Returns: datetime object for valid timestamps, datetime.max for unparseable ones.
        """
        ts_str = event.get("timestamp", "")
        parsed = AnalysisUtils.parse_datetime(ts_str)
        return parsed if parsed else datetime.max


class TextMetrics:
    """Basic text analysis metrics for offline mode."""
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words. For CJK, count characters. For Latin, count words by whitespace.
        Excludes punctuation.
        """
        if not text: return 0
        
        # Count CJK characters
        cjk_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # Remove CJK chars
        non_cjk_text = re.sub(r'[\u4e00-\u9fff]', ' ', text)
        
        # Remove punctuation (keep alphanumeric only)
        # Using a simple regex for common punctuation
        clean_text = re.sub(r'[^\w\s]', ' ', non_cjk_text)
        
        other_count = len(clean_text.split())
        
        return cjk_count + other_count

    @staticmethod
    def count_sentences(text: str) -> int:
        """Approximation of sentence count based on punctuation."""
        if not text: return 0
        return len(re.findall(r'[。！？.!?]+', text))

    @staticmethod
    def count_unique_terms(text: str) -> int:
        """Count unique CJK characters and Latin words."""
        if not text: return 0
        cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)
        non_cjk_text = re.sub(r'[\u4e00-\u9fff]', ' ', text).lower()
        latin_words = non_cjk_text.split()
        return len(set(cjk_chars + latin_words))

    @staticmethod
    def get_avg_sentence_length(text: str) -> float:
        s_count = TextMetrics.count_sentences(text)
        if s_count == 0: return 0.0
        w_count = TextMetrics.count_words(text)
        return w_count / s_count


