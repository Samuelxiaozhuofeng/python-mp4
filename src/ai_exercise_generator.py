"""
AI Exercise Generator
Uses AI service to generate personalized listening fill-in-the-blank exercises based on user level
"""
import json
import requests
from typing import List, Dict, Optional, Tuple
from PySide6.QtCore import QObject, Signal, QThread
from config import config

class AIExerciseGenerator(QObject):
    """AI Exercise Generator"""
    
    # Signal definition
    generation_started = Signal()
    generation_finished = Signal(bool, str, list)  # Success/failure, message, exercise data
    progress_updated = Signal(int)  # Progress percentage
    
    def __init__(self):
        super().__init__()
        self.ai_config = config.get_ai_config()
    
    def generate_exercises(self, subtitles: List, exercise_config: Dict) -> None:
        """Generate exercise data"""
        self.generation_started.emit()
        
        try:
            # Validate AI configuration
            if not self.ai_config.get('api_key') or not self.ai_config.get('api_url'):
                self.generation_finished.emit(False, "Please configure AI service first", [])
                return
            
            # Batch process subtitles
            exercises = []
            total_subtitles = len(subtitles)
            batch_size = 10  # Reduce batch size to improve success rate
            
            # Process by batch
            for batch_start in range(0, total_subtitles, batch_size):
                batch_end = min(batch_start + batch_size, total_subtitles)
                batch_subtitles = subtitles[batch_start:batch_end]
                
                # Update progress
                progress = int((batch_end) / total_subtitles * 100)
                self.progress_updated.emit(progress)
                
                print(f"[DEBUG] Processing batch {batch_start//batch_size + 1}: {batch_start+1}-{batch_end} sentences")
                
                # Batch generate exercises
                batch_exercises = self.generate_batch_exercises(batch_subtitles, exercise_config, batch_start, total_subtitles)
                
                if batch_exercises:
                    exercises.extend(batch_exercises)
                else:
                    # Batch processing failed, fallback to individual processing
                    print(f"[DEBUG] Batch processing failed, falling back to individual processing")
                    for i, subtitle in enumerate(batch_subtitles):
                        exercise = self.generate_single_exercise(subtitle, exercise_config, batch_start + i + 1, total_subtitles)
                        if exercise:
                            exercises.append(exercise)
            
            self.generation_finished.emit(True, f"Successfully generated {len(exercises)} exercises", exercises)
            
        except Exception as e:
            self.generation_finished.emit(False, f"Generation failed: {str(e)}", [])
    
    def generate_batch_exercises(self, batch_subtitles: List, exercise_config: Dict, batch_start_index: int, total_subtitles: int) -> Optional[List[Dict]]:
        """批量生成练习"""
        try:
            # 构建批量AI请求
            prompt = self.build_batch_prompt(batch_subtitles, exercise_config)
            
            # 调用AI服务
            response = self.call_ai_service(prompt)
            
            if response:
                # 解析AI返回的批量结果
                batch_results = self.parse_batch_ai_response(response, batch_subtitles, batch_start_index, total_subtitles)
                return batch_results
            
        except Exception as e:
            print(f"批量生成练习失败: {e}")
            return None
    
    def generate_single_exercise(self, subtitle, exercise_config: Dict, current: int, total: int) -> Optional[Dict]:
        """为单个字幕生成练习"""
        try:
            # 构建AI请求
            prompt = self.build_prompt(subtitle.text, exercise_config)
            
            # 调用AI服务
            response = self.call_ai_service(prompt)
            
            if response:
                # 解析AI返回的结果
                blanks_data = self.parse_ai_response(response, subtitle.text)
                
                return {
                    'original_text': subtitle.text,
                    'blanks': blanks_data,
                    'current': current,
                    'total': total,
                    'subtitle_index': subtitle.index,
                    'start_time': subtitle.start_time,
                    'end_time': subtitle.end_time
                }
        
        except Exception as e:
            print(f"生成单个练习失败: {e}")
            return None
    
    def build_prompt(self, text: str, config: Dict) -> str:
        """构建AI提示词"""
        language = config.get('language', 'English')
        level = config.get('level', 'B1-B2')
        focus_areas = config.get('focus_areas', ['名词', '动词'])
        blank_density = config.get('blank_density', 25)
        
        # 计算建议的挖空数量
        words = text.split()
        suggested_blanks = max(1, int(len(words) * blank_density / 100))
        
        # 根据语言调整提示词
        language_info = self._get_language_info(language)
        
        prompt = f"""你是一个专业的{language_info['name']}学习助手。请为以下{language_info['name']}句子创建听力填空练习。

句子: "{text}"

要求:
1. 目标语言: {language_info['name']}
2. 学习者水平: {level} ({language_info['level_desc']})
3. 重点挖空类型: {', '.join(focus_areas)}
4. 挖空密度: 约{blank_density}% (建议挖空{suggested_blanks}个词)

挖空原则:
- 选择对该水平{language_info['name']}学习者有挑战性但不过难的词汇
- 优先选择{', '.join(focus_areas)}类型的词汇
- 避免挖空{language_info['function_words']}
- 考虑{language_info['grammar_focus']}
- 确保挖空后句子仍然有意义且符合{language_info['name']}语法规则

提示生成要求:
- 提示应该用中文表述
- 包含词性信息（如：名词、动词、形容词等）
- 可以包含首字母提示
- 对于复杂词汇可以给出含义提示

请以JSON格式返回结果:
{{
    "blanks": [
        {{
            "position": 词在句子中的位置(从0开始),
            "word": "被挖空的原词",
            "hint": "给学习者的中文提示(如：名词，表示食物，首字母是f)",
            "difficulty": "该词的难度级别(easy/medium/hard)"
        }}
    ]
}}

只返回JSON，不要其他文字。"""
        
        return prompt
    
    def _get_language_info(self, language: str) -> Dict[str, str]:
        """获取语言特定信息"""
        language_configs = {
            'English': {
                'name': '英语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如the, a, is, and等)',
                'grammar_focus': '动词时态、介词搭配、冠词使用'
            },
            'Spanish': {
                'name': '西班牙语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如el, la, es, y等)',
                'grammar_focus': '动词变位、性别一致、语序规则'
            },
            'French': {
                'name': '法语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如le, la, est, et等)',
                'grammar_focus': '动词变位、性别一致、语音连读'
            },
            'German': {
                'name': '德语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如der, die, ist, und等)',
                'grammar_focus': '格变、动词位置、复合词构成'
            },
            'Italian': {
                'name': '意大利语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如il, la, è, e等)',
                'grammar_focus': '动词变位、性别一致、语调变化'
            },
            'Portuguese': {
                'name': '葡萄牙语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如o, a, é, e等)',
                'grammar_focus': '动词变位、鼻音化、语序规则'
            },
            'Russian': {
                'name': '俄语',
                'level_desc': 'CEFR标准',
                'function_words': '功能词(如и, в, на, с等)',
                'grammar_focus': '格变系统、动词体、软硬辅音'
            },
            'Japanese': {
                'name': '日语',
                'level_desc': 'JLPT标准',
                'function_words': '助词(如は, が, を, に等)',
                'grammar_focus': '助词使用、敬语系统、动词活用'
            },
            'Korean': {
                'name': '韩语',
                'level_desc': 'TOPIK标准',
                'function_words': '助词(如은/는, 이/가, 을/를等)',
                'grammar_focus': '助词使用、敬语系统、动词活用'
            },
            'Chinese': {
                'name': '中文',
                'level_desc': 'HSK标准',
                'function_words': '功能词(如的, 了, 在, 和等)',
                'grammar_focus': '语序规则、量词使用、语气助词'
            }
        }
        
        return language_configs.get(language, language_configs['English'])
    
    def build_batch_prompt(self, batch_subtitles: List, config: Dict) -> str:
        """构建批量AI提示词"""
        language = config.get('language', 'English')
        level = config.get('level', 'B1-B2')
        focus_areas = config.get('focus_areas', ['名词', '动词'])
        blank_density = config.get('blank_density', 25)
        
        # 根据语言调整提示词
        language_info = self._get_language_info(language)
        
        # 构建批量句子列表
        sentences_text = ""
        for i, subtitle in enumerate(batch_subtitles):
            sentences_text += f"{i+1}. \"{subtitle.text}\"\n"
        
        prompt = f"""为以下{len(batch_subtitles)}个{language_info['name']}句子创建听力填空练习。

句子列表:
{sentences_text}

要求:
- 目标语言: {language_info['name']}
- 学习者水平: {level}
- 重点挖空: {', '.join(focus_areas)}
- 每句1-2个挖空
- 提示用中文，包含词性和首字母

重要：请返回标准的紧凑JSON格式，不要在JSON字符串中插入换行符或特殊字符。

返回格式示例:
{{"exercises": [{{"sentence_index": 1, "blanks": [{{"position": 0, "word": "example", "hint": "名词，首字母e", "difficulty": "medium"}}]}}]}}"""
        
        return prompt
    
    def parse_batch_ai_response(self, response: str, batch_subtitles: List, batch_start_index: int, total_subtitles: int) -> List[Dict]:
        """解析批量AI返回的结果"""
        try:
            # 清理响应内容
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # 尝试修复常见的JSON格式问题
            response = self._fix_json_format(response)
            
            print(f"[DEBUG] 尝试解析批量响应，长度: {len(response)}")
            print(f"[DEBUG] 修复后的响应前300字符: {response[:300]}")
            
            # 验证JSON格式
            if not response.strip().startswith('{'):
                print(f"[DEBUG] 响应不是以{{开头: {response[:50]}")
                return None
            
            data = json.loads(response)
            exercises_data = data.get('exercises', [])
            
            print(f"[DEBUG] 解析到 {len(exercises_data)} 个练习数据")
            
            results = []
            
            for exercise_data in exercises_data:
                sentence_index = exercise_data.get('sentence_index', 1) - 1  # 转换为0索引
                
                # 确保索引有效
                if 0 <= sentence_index < len(batch_subtitles):
                    subtitle = batch_subtitles[sentence_index]
                    blanks = exercise_data.get('blanks', [])
                    
                    # 验证和清理挖空数据
                    valid_blanks = self.validate_blanks(blanks, subtitle.text)
                    
                    result = {
                        'original_text': subtitle.text,
                        'blanks': valid_blanks,
                        'current': batch_start_index + sentence_index + 1,
                        'total': total_subtitles,
                        'subtitle_index': subtitle.index,
                        'start_time': subtitle.start_time,
                        'end_time': subtitle.end_time
                    }
                    results.append(result)
                else:
                    print(f"[DEBUG] 跳过无效索引: {sentence_index}")
            
            print(f"[DEBUG] 批量解析成功，返回 {len(results)} 个练习")
            return results if results else None
            
        except json.JSONDecodeError as e:
            print(f"批量JSON解析失败: {e}")
            print(f"AI返回内容前200字符: {response[:200]}...")
            return None
        
        except Exception as e:
            print(f"批量解析AI响应失败: {e}")
            return None
    
    def _fix_json_format(self, response: str) -> str:
        """修复常见的JSON格式问题"""
        try:
            import re
            
            # 移除可能的BOM标记
            if response.startswith('\ufeff'):
                response = response[1:]
            
            # 修复AI在JSON字符串中插入的换行符和控制字符
            # 这是最常见的问题：AI在字符串值中插入了换行符
            response = re.sub(r'"\s*\n\s*', '"', response)  # 移除字符串后的换行
            response = re.sub(r'\n\s*"', '"', response)     # 移除字符串前的换行
            
            # 移除JSON中的控制字符（除了必要的\n, \t, \r）
            response = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', response)
            
            # 修复常见的格式问题
            response = re.sub(r',\s*}', '}', response)      # 移除对象末尾多余的逗号
            response = re.sub(r',\s*]', ']', response)      # 移除数组末尾多余的逗号
            
            # 确保JSON完整性
            if not response.strip().endswith('}'):
                # 尝试找到最后一个完整的对象
                last_brace = response.rfind('}')
                if last_brace > 0:
                    # 找到可能的数组结束位置
                    last_bracket = response.rfind(']', 0, last_brace + 1)
                    if last_bracket > 0:
                        response = response[:last_bracket + 1] + '}'
            
            return response.strip()
        except Exception as e:
            print(f"[DEBUG] JSON修复失败: {e}")
            return response
    
    def validate_blanks(self, blanks: List[Dict], original_text: str) -> List[Dict]:
        """验证挖空数据"""
        words = original_text.split()
        valid_blanks = []
        
        for blank in blanks:
            position = blank.get('position', -1)
            word = blank.get('word', '').strip()
            
            # 验证位置和词汇是否匹配
            if 0 <= position < len(words):
                expected_word = words[position].strip('.,!?;:"()[]{}')
                if word.lower() == expected_word.lower():
                    valid_blanks.append({
                        'position': position,
                        'answer': expected_word,
                        'hint': blank.get('hint', f"{len(expected_word)} letters"),
                        'difficulty': blank.get('difficulty', 'medium')
                    })
        
        return valid_blanks
    
    def call_ai_service(self, prompt: str) -> Optional[str]:
        """调用AI服务"""
        try:
            headers = {
                "Authorization": f"Bearer {self.ai_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.ai_config.get('model', 'gpt-3.5-turbo'),
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的多语言学习助手，专门创建高质量的听力填空练习。请确保返回完整、有效的JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,  # 增加token限制以支持批量处理
                "temperature": 0.1,  # 降低随机性，提高JSON格式稳定性
                "response_format": {"type": "json_object"}  # 强制JSON格式输出
            }
            
            # 增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    timeout = self.ai_config.get('timeout', 60)  # 增加超时时间
                    response = requests.post(
                        self.ai_config['api_url'],
                        json=data,
                        headers=headers,
                        timeout=timeout
                    )
                    break  # 成功则跳出重试循环
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    print(f"[DEBUG] API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        raise  # 最后一次尝试失败则抛出异常
                    import time
                    time.sleep(2)  # 等待2秒后重试
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
            else:
                print(f"AI服务返回错误: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"调用AI服务失败: {e}")
        
        return None
    
    def test_json_fix(self):
        """测试JSON修复功能"""
        test_response = '''{
    "exercises": ["
        {
            "sentence_index": 1,"
            "blanks": ["
                {
                    "position": 1,"
                    "word": "diferencia","
                    "hint": "名词，首字母d",
                    "difficulty": "medium"
                }
            ]
        }
    ]
}'''
        print("[DEBUG] 测试JSON修复功能")
        print(f"原始响应: {test_response}")
        fixed = self._fix_json_format(test_response)
        print(f"修复后响应: {fixed}")
        
        try:
            import json
            data = json.loads(fixed)
            print("[DEBUG] JSON修复成功！")
            return True
        except Exception as e:
            print(f"[DEBUG] JSON修复失败: {e}")
            return False
    
    def parse_ai_response(self, response: str, original_text: str) -> List[Dict]:
        """解析AI返回的结果"""
        try:
            # 尝试解析JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response)
            blanks = data.get('blanks', [])
            
            # 验证和清理数据
            words = original_text.split()
            valid_blanks = []
            
            for blank in blanks:
                position = blank.get('position', -1)
                word = blank.get('word', '').strip()
                
                # 验证位置和词汇是否匹配
                if 0 <= position < len(words):
                    expected_word = words[position].strip('.,!?;:"()[]{}')
                    if word.lower() == expected_word.lower():
                        valid_blanks.append({
                            'position': position,
                            'answer': expected_word,
                            'hint': blank.get('hint', f"{len(expected_word)} letters"),
                            'difficulty': blank.get('difficulty', 'medium')
                        })
            
            return valid_blanks
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"AI返回内容: {response}")
            
            # 如果JSON解析失败，尝试简单的文本解析
            return self.fallback_parsing(response, original_text)
        
        except Exception as e:
            print(f"解析AI响应失败: {e}")
            return []
    
    def fallback_parsing(self, response: str, original_text: str) -> List[Dict]:
        """备用解析方法"""
        try:
            words = original_text.split()
            # 简单的备用方案：随机选择1-2个词
            import random
            num_blanks = min(2, len(words) // 3 + 1)
            positions = random.sample(range(len(words)), min(num_blanks, len(words)))
            
            blanks = []
            for pos in sorted(positions):
                word = words[pos].strip('.,!?;:"()[]{}')
                blanks.append({
                    'position': pos,
                    'answer': word,
                    'hint': f"{len(word)} letters",
                    'difficulty': 'medium'
                })
            
            return blanks
            
        except Exception as e:
            print(f"备用解析也失败: {e}")
            return []

class AIExerciseThread(QThread):
    """AI练习生成线程"""
    
    # Signal definition
    generation_started = Signal()
    generation_finished = Signal(bool, str, list)
    progress_updated = Signal(int)
    
    def __init__(self, subtitles: List, exercise_config: Dict):
        super().__init__()
        self.subtitles = subtitles
        self.exercise_config = exercise_config
        self.generator = AIExerciseGenerator()
        
        # 连接信号
        self.generator.generation_started.connect(self.generation_started.emit)
        self.generator.generation_finished.connect(self.generation_finished.emit)
        self.generator.progress_updated.connect(self.progress_updated.emit)
    
    def run(self):
        """运行AI生成"""
        self.generator.generate_exercises(self.subtitles, self.exercise_config)
