"""
Subtitle parsing module
Handles parsing, validation and time synchronization of SRT subtitle files
"""
import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import pysrt
from PySide6.QtCore import QObject, Signal

@dataclass
class SubtitleItem:
    """Subtitle item data class"""
    index: int
    start_time: int  # milliseconds
    end_time: int    # milliseconds
    text: str
    duration: int = 0    # milliseconds, default value
    
    def __post_init__(self):
        self.duration = self.end_time - self.start_time
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'index': self.index,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'text': self.text,
            'duration': self.duration
        }

class SubtitleParser(QObject):
    """Subtitle parser"""
    
    # Define signals
    parsing_started = Signal()
    parsing_finished = Signal(bool, str)  # Success/failure, message
    progress_updated = Signal(int)  # Progress percentage
    
    def __init__(self):
        super().__init__()
        self.subtitles: List[SubtitleItem] = []
        self.current_file = None
        self.time_offset = 0  # Time offset (milliseconds)
    
    def load_srt_file(self, file_path: str) -> bool:
        """Load SRT subtitle file"""
        if not os.path.exists(file_path):
            self.parsing_finished.emit(False, f"File does not exist: {file_path}")
            return False
        
        if not file_path.lower().endswith('.srt'):
            self.parsing_finished.emit(False, "Unsupported file format, please select SRT file")
            return False
        
        try:
            self.parsing_started.emit()
            
            # Use pysrt to parse SRT file
            srt_file = pysrt.open(file_path, encoding='utf-8')
            
            if not srt_file:
                # Try other encodings
                encodings = ['gbk', 'gb2312', 'latin-1', 'cp1252']
                for encoding in encodings:
                    try:
                        srt_file = pysrt.open(file_path, encoding=encoding)
                        if srt_file:
                            break
                    except:
                        continue
            
            if not srt_file:
                self.parsing_finished.emit(False, "Unable to parse subtitle file, please check file format and encoding")
                return False
            
            # Convert to internal format
            self.subtitles = []
            total_items = len(srt_file)
            
            for i, item in enumerate(srt_file):
                # Update progress
                progress = int((i + 1) / total_items * 100)
                self.progress_updated.emit(progress)
                
                # Convert time format (pysrt uses milliseconds)
                start_ms = self._time_to_milliseconds(item.start)
                end_ms = self._time_to_milliseconds(item.end)
                
                # Clean text (remove HTML tags, etc.)
                clean_text = self._clean_text(item.text)
                
                subtitle_item = SubtitleItem(
                    index=item.index,
                    start_time=start_ms,
                    end_time=end_ms,
                    text=clean_text
                )
                
                self.subtitles.append(subtitle_item)
            
            self.current_file = file_path
            self.parsing_finished.emit(True, f"Successfully loaded {len(self.subtitles)} subtitles")
            return True
            
        except Exception as e:
            self.parsing_finished.emit(False, f"Parsing failed: {str(e)}")
            return False
    
    def _time_to_milliseconds(self, time_obj) -> int:
        """Convert pysrt time object to milliseconds"""
        return (time_obj.hours * 3600 + 
                time_obj.minutes * 60 + 
                time_obj.seconds) * 1000 + time_obj.milliseconds
    
    def _clean_text(self, text: str) -> str:
        """Clean subtitle text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading and trailing whitespace
        text = text.strip()
        
        return text
    
    def get_subtitle_at_time(self, time_ms: int) -> Optional[SubtitleItem]:
        """Get subtitle at specified time point"""
        adjusted_time = time_ms - self.time_offset
        
        for subtitle in self.subtitles:
            if subtitle.start_time <= adjusted_time <= subtitle.end_time:
                return subtitle
        
        return None
    
    def get_subtitles_in_range(self, start_ms: int, end_ms: int) -> List[SubtitleItem]:
        """Get subtitles within specified time range"""
        result = []
        adjusted_start = start_ms - self.time_offset
        adjusted_end = end_ms - self.time_offset
        
        for subtitle in self.subtitles:
            # Check if subtitle overlaps with time range
            if (subtitle.start_time <= adjusted_end and 
                subtitle.end_time >= adjusted_start):
                result.append(subtitle)
        
        return result
    
    def set_time_offset(self, offset_ms: int):
        """Set time offset"""
        self.time_offset = offset_ms
    
    def get_time_offset(self) -> int:
        """Get current time offset"""
        return self.time_offset
    
    def validate_timing(self, video_duration_ms: int) -> Dict[str, any]:
        """Validate subtitle timing"""
        if not self.subtitles:
            return {
                'valid': False,
                'issues': ['No subtitle data'],
                'suggestions': []
            }
        
        issues = []
        suggestions = []
        
        # Check if subtitles exceed video duration
        last_subtitle = max(self.subtitles, key=lambda x: x.end_time)
        if last_subtitle.end_time > video_duration_ms:
            issues.append(f"Subtitle end time ({self._ms_to_time_string(last_subtitle.end_time)}) exceeds video duration ({self._ms_to_time_string(video_duration_ms)})")
            suggestions.append("Consider adjusting subtitle time offset")
        
        # Check subtitle intervals
        overlapping_count = 0
        gap_issues = 0
        
        for i in range(len(self.subtitles) - 1):
            current = self.subtitles[i]
            next_sub = self.subtitles[i + 1]
            
            # Check for overlap
            if current.end_time > next_sub.start_time:
                overlapping_count += 1
            
            # Check for large gaps
            gap = next_sub.start_time - current.end_time
            if gap > 5000:  # 5 seconds
                gap_issues += 1
        
        if overlapping_count > 0:
            issues.append(f"Found {overlapping_count} subtitle time overlaps")
        
        if gap_issues > len(self.subtitles) * 0.3:  # More than 30% have large gaps
            issues.append(f"Found {gap_issues} subtitle intervals too large")
            suggestions.append("Check subtitle and video synchronization")
        
        # Check subtitle length
        too_short = sum(1 for s in self.subtitles if s.duration < 500)  # 0.5 seconds
        too_long = sum(1 for s in self.subtitles if s.duration > 10000)  # 10 seconds
        
        if too_short > 0:
            issues.append(f"{too_short} subtitles have too short duration")
        
        if too_long > 0:
            issues.append(f"{too_long} subtitles have too long duration")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions,
            'stats': {
                'total_subtitles': len(self.subtitles),
                'overlapping': overlapping_count,
                'gaps': gap_issues,
                'too_short': too_short,
                'too_long': too_long
            }
        }
    
    def _ms_to_time_string(self, ms: int) -> str:
        """Convert milliseconds to time string"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
    
    def get_subtitle_stats(self) -> Dict[str, any]:
        """Get subtitle statistics"""
        if not self.subtitles:
            return {}
        
        total_duration = sum(s.duration for s in self.subtitles)
        avg_duration = total_duration / len(self.subtitles)
        
        first_subtitle = min(self.subtitles, key=lambda x: x.start_time)
        last_subtitle = max(self.subtitles, key=lambda x: x.end_time)
        
        return {
            'total_count': len(self.subtitles),
            'total_duration_ms': total_duration,
            'avg_duration_ms': avg_duration,
            'first_start_time': first_subtitle.start_time,
            'last_end_time': last_subtitle.end_time,
            'time_span_ms': last_subtitle.end_time - first_subtitle.start_time,
            'current_file': self.current_file,
            'time_offset_ms': self.time_offset
        }
    
    def export_adjusted_srt(self, output_path: str) -> bool:
        """Export adjusted SRT file"""
        if not self.subtitles:
            return False
        
        try:
            srt_file = pysrt.SubRipFile()
            
            for subtitle in self.subtitles:
                # Apply time offset
                adjusted_start = subtitle.start_time + self.time_offset
                adjusted_end = subtitle.end_time + self.time_offset
                
                # Convert back to pysrt time format
                start_time = self._milliseconds_to_time(adjusted_start)
                end_time = self._milliseconds_to_time(adjusted_end)
                
                item = pysrt.SubRipItem(
                    index=subtitle.index,
                    start=start_time,
                    end=end_time,
                    text=subtitle.text
                )
                
                srt_file.append(item)
            
            srt_file.save(output_path, encoding='utf-8')
            return True
            
        except Exception as e:
            print(f"Failed to export SRT file: {e}")
            return False
    
    def _milliseconds_to_time(self, ms: int):
        """Convert milliseconds to pysrt time object"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        
        return pysrt.SubRipTime(hours, minutes, seconds, milliseconds)
    
    def clear(self):
        """Clear current subtitle data"""
        self.subtitles = []
        self.current_file = None
        self.time_offset = 0
