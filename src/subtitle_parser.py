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
        """将pysrt时间对象转换为毫秒"""
        return (time_obj.hours * 3600 + 
                time_obj.minutes * 60 + 
                time_obj.seconds) * 1000 + time_obj.milliseconds
    
    def _clean_text(self, text: str) -> str:
        """清理字幕文本"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除首尾空白
        text = text.strip()
        
        return text
    
    def get_subtitle_at_time(self, time_ms: int) -> Optional[SubtitleItem]:
        """获取指定时间点的字幕"""
        adjusted_time = time_ms - self.time_offset
        
        for subtitle in self.subtitles:
            if subtitle.start_time <= adjusted_time <= subtitle.end_time:
                return subtitle
        
        return None
    
    def get_subtitles_in_range(self, start_ms: int, end_ms: int) -> List[SubtitleItem]:
        """获取指定时间范围内的字幕"""
        result = []
        adjusted_start = start_ms - self.time_offset
        adjusted_end = end_ms - self.time_offset
        
        for subtitle in self.subtitles:
            # 检查字幕是否与时间范围有重叠
            if (subtitle.start_time <= adjusted_end and 
                subtitle.end_time >= adjusted_start):
                result.append(subtitle)
        
        return result
    
    def set_time_offset(self, offset_ms: int):
        """设置时间偏移量"""
        self.time_offset = offset_ms
    
    def get_time_offset(self) -> int:
        """获取当前时间偏移量"""
        return self.time_offset
    
    def validate_timing(self, video_duration_ms: int) -> Dict[str, any]:
        """验证字幕时间是否合理"""
        if not self.subtitles:
            return {
                'valid': False,
                'issues': ['没有字幕数据'],
                'suggestions': []
            }
        
        issues = []
        suggestions = []
        
        # 检查字幕是否超出视频时长
        last_subtitle = max(self.subtitles, key=lambda x: x.end_time)
        if last_subtitle.end_time > video_duration_ms:
            issues.append(f"字幕结束时间({self._ms_to_time_string(last_subtitle.end_time)}) 超出视频时长({self._ms_to_time_string(video_duration_ms)})")
            suggestions.append("考虑调整字幕时间偏移")
        
        # 检查字幕间隔
        overlapping_count = 0
        gap_issues = 0
        
        for i in range(len(self.subtitles) - 1):
            current = self.subtitles[i]
            next_sub = self.subtitles[i + 1]
            
            # 检查重叠
            if current.end_time > next_sub.start_time:
                overlapping_count += 1
            
            # 检查间隔过大
            gap = next_sub.start_time - current.end_time
            if gap > 5000:  # 5秒
                gap_issues += 1
        
        if overlapping_count > 0:
            issues.append(f"发现 {overlapping_count} 处字幕时间重叠")
        
        if gap_issues > len(self.subtitles) * 0.3:  # 超过30%的间隔过大
            issues.append(f"发现 {gap_issues} 处字幕间隔过大")
            suggestions.append("检查字幕与视频的同步性")
        
        # 检查字幕长度
        too_short = sum(1 for s in self.subtitles if s.duration < 500)  # 0.5秒
        too_long = sum(1 for s in self.subtitles if s.duration > 10000)  # 10秒
        
        if too_short > 0:
            issues.append(f"{too_short} 条字幕持续时间过短")
        
        if too_long > 0:
            issues.append(f"{too_long} 条字幕持续时间过长")
        
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
        """将毫秒转换为时间字符串"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
    
    def get_subtitle_stats(self) -> Dict[str, any]:
        """获取字幕统计信息"""
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
        """导出调整后的SRT文件"""
        if not self.subtitles:
            return False
        
        try:
            srt_file = pysrt.SubRipFile()
            
            for subtitle in self.subtitles:
                # 应用时间偏移
                adjusted_start = subtitle.start_time + self.time_offset
                adjusted_end = subtitle.end_time + self.time_offset
                
                # 转换回pysrt时间格式
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
            print(f"导出SRT文件失败: {e}")
            return False
    
    def _milliseconds_to_time(self, ms: int):
        """将毫秒转换为pysrt时间对象"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        
        return pysrt.SubRipTime(hours, minutes, seconds, milliseconds)
    
    def clear(self):
        """清除当前字幕数据"""
        self.subtitles = []
        self.current_file = None
        self.time_offset = 0
