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
        """Generate batch exercises"""
        try:
            # Build batch AI request
            prompt = self.build_batch_prompt(batch_subtitles, exercise_config)
            
            # Call AI service
            response = self.call_ai_service(prompt)
            
            if response:
                # Parse batch AI response
                batch_results = self.parse_batch_ai_response(response, batch_subtitles, batch_start_index, total_subtitles)
                return batch_results
            
        except Exception as e:
            print(f"Batch exercise generation failed: {e}")
            return None
    
    def generate_single_exercise(self, subtitle, exercise_config: Dict, current: int, total: int) -> Optional[Dict]:
        """Generate exercise for single subtitle"""
        try:
            # Build AI request
            prompt = self.build_prompt(subtitle.text, exercise_config)
            
            # Call AI service
            response = self.call_ai_service(prompt)
            
            if response:
                # Parse AI response
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
            print(f"Single exercise generation failed: {e}")
            return None
    
    def build_prompt(self, text: str, config: Dict) -> str:
        """Build AI prompt"""
        language = config.get('language', 'English')
        level = config.get('level', 'B1-B2')
        focus_areas = config.get('focus_areas', ['nouns', 'verbs'])
        blank_density = config.get('blank_density', 25)
        
        # Calculate suggested number of blanks
        words = text.split()
        suggested_blanks = max(1, int(len(words) * blank_density / 100))
        
        # Adjust prompt based on language
        language_info = self._get_language_info(language)
        
        prompt = f"""You are a professional {language_info['name']} learning assistant. Please create listening fill-in-the-blank exercises for the following {language_info['name']} sentence.

Sentence: "{text}"

Requirements:
1. Target language: {language_info['name']}
2. Learner level: {level} ({language_info['level_desc']})
3. Focus blank types: {', '.join(focus_areas)}
4. Blank density: approximately {blank_density}% (suggested {suggested_blanks} blanks)

Blank principles:
- Choose vocabulary that is challenging but not too difficult for {language_info['name']} learners at this level
- Prioritize {', '.join(focus_areas)} type vocabulary
- Avoid blanking {language_info['function_words']}
- Consider {language_info['grammar_focus']}
- Ensure the sentence remains meaningful and follows {language_info['name']} grammar rules after blanking

Hint generation requirements:
- Hints should be expressed in Chinese
- Include part-of-speech information (e.g., noun, verb, adjective, etc.)
- Can include first letter hints
- For complex vocabulary, provide meaning hints

Please return results in JSON format:
{{
    "blanks": [
        {{
            "position": word position in sentence (starting from 0),
            "word": "original word to be blanked",
            "hint": "Chinese hint for learners (e.g., noun, represents food, first letter is f)",
            "difficulty": "difficulty level of the word (easy/medium/hard)"
        }}
    ]
}}

Return only JSON, no other text."""
        
        return prompt
    
    def _get_language_info(self, language: str) -> Dict[str, str]:
        """Get language-specific information"""
        language_configs = {
            'English': {
                'name': 'English',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as the, a, is, and, etc.)',
                'grammar_focus': 'verb tenses, preposition collocations, article usage'
            },
            'Spanish': {
                'name': 'Spanish',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as el, la, es, y, etc.)',
                'grammar_focus': 'verb conjugation, gender agreement, word order rules'
            },
            'French': {
                'name': 'French',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as le, la, est, et, etc.)',
                'grammar_focus': 'verb conjugation, gender agreement, liaison'
            },
            'German': {
                'name': 'German',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as der, die, ist, und, etc.)',
                'grammar_focus': 'case declension, verb position, compound word formation'
            },
            'Italian': {
                'name': 'Italian',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as il, la, è, e, etc.)',
                'grammar_focus': 'verb conjugation, gender agreement, intonation changes'
            },
            'Portuguese': {
                'name': 'Portuguese',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as o, a, é, e, etc.)',
                'grammar_focus': 'verb conjugation, nasalization, word order rules'
            },
            'Russian': {
                'name': 'Russian',
                'level_desc': 'CEFR standard',
                'function_words': 'function words (such as и, в, на, с, etc.)',
                'grammar_focus': 'case system, verb aspect, hard and soft consonants'
            },
            'Japanese': {
                'name': 'Japanese',
                'level_desc': 'JLPT standard',
                'function_words': 'particles (such as は, が, を, に, etc.)',
                'grammar_focus': 'particle usage, honorific system, verb conjugation'
            },
            'Korean': {
                'name': 'Korean',
                'level_desc': 'TOPIK standard',
                'function_words': 'particles (such as 은/는, 이/가, 을/를, etc.)',
                'grammar_focus': 'particle usage, honorific system, verb conjugation'
            },
            'Chinese': {
                'name': 'Chinese',
                'level_desc': 'HSK standard',
                'function_words': 'function words (such as de, le, zai, he, etc.)',
                'grammar_focus': 'word order rules, classifier usage, modal particles'
            }
        }
        
        return language_configs.get(language, language_configs['English'])
    
    def build_batch_prompt(self, batch_subtitles: List, config: Dict) -> str:
        """Build batch AI prompt"""
        language = config.get('language', 'English')
        level = config.get('level', 'B1-B2')
        focus_areas = config.get('focus_areas', ['nouns', 'verbs'])
        blank_density = config.get('blank_density', 25)
        
        # Adjust prompt based on language
        language_info = self._get_language_info(language)
        
        # Build batch sentence list
        sentences_text = ""
        for i, subtitle in enumerate(batch_subtitles):
            sentences_text += f"{i+1}. \"{subtitle.text}\"\n"
        
        prompt = f"""Create listening fill-in-the-blank exercises for the following {len(batch_subtitles)} {language_info['name']} sentences.

Sentence list:
{sentences_text}

Requirements:
- Target language: {language_info['name']}
- Learner level: {level}
- Focus blanks: {', '.join(focus_areas)}
- 1-2 blanks per sentence
- Hints in Chinese, include part-of-speech and first letter

Important: Please return standard compact JSON format, do not insert line breaks or special characters in JSON strings.

Return format example:
{{"exercises": [{{"sentence_index": 1, "blanks": [{{"position": 0, "word": "example", "hint": "noun, first letter e", "difficulty": "medium"}}]}}]}}"""
        
        return prompt
    
    def parse_batch_ai_response(self, response: str, batch_subtitles: List, batch_start_index: int, total_subtitles: int) -> List[Dict]:
        """Parse batch AI response"""
        try:
            # Clean response content
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Try to fix common JSON format issues
            response = self._fix_json_format(response)
            
            print(f"[DEBUG] Attempting to parse batch response, length: {len(response)}")
            print(f"[DEBUG] Fixed response first 300 characters: {response[:300]}")
            
            # Validate JSON format
            if not response.strip().startswith('{'):
                print(f"[DEBUG] Response does not start with {{: {response[:50]}")
                return None
            
            data = json.loads(response)
            exercises_data = data.get('exercises', [])
            
            print(f"[DEBUG] Parsed {len(exercises_data)} exercise data")
            
            results = []
            
            for exercise_data in exercises_data:
                sentence_index = exercise_data.get('sentence_index', 1) - 1  # Convert to 0-based index
                
                # Ensure index is valid
                if 0 <= sentence_index < len(batch_subtitles):
                    subtitle = batch_subtitles[sentence_index]
                    blanks = exercise_data.get('blanks', [])
                    
                    # Validate and clean blank data
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
                    print(f"[DEBUG] Skipping invalid index: {sentence_index}")
            
            print(f"[DEBUG] Batch parsing successful, returning {len(results)} exercises")
            return results if results else None
            
        except json.JSONDecodeError as e:
            print(f"Batch JSON parsing failed: {e}")
            print(f"AI response first 200 characters: {response[:200]}...")
            return None
        
        except Exception as e:
            print(f"Batch parsing AI response failed: {e}")
            return None
    
    def _fix_json_format(self, response: str) -> str:
        """Fix common JSON format issues"""
        try:
            import re
            
            # Remove possible BOM marker
            if response.startswith('\ufeff'):
                response = response[1:]
            
            # Fix line breaks and control characters inserted by AI in JSON strings
            # This is the most common issue: AI inserts line breaks in string values
            response = re.sub(r'"\s*\n\s*', '"', response)  # Remove line breaks after strings
            response = re.sub(r'\n\s*"', '"', response)     # Remove line breaks before strings
            
            # Remove control characters in JSON (except necessary \n, \t, \r)
            response = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', response)
            
            # Fix common format issues
            response = re.sub(r',\s*}', '}', response)      # Remove extra commas at end of objects
            response = re.sub(r',\s*]', ']', response)      # Remove extra commas at end of arrays
            
            # Ensure JSON completeness
            if not response.strip().endswith('}'):
                # Try to find the last complete object
                last_brace = response.rfind('}')
                if last_brace > 0:
                    # Find possible array end position
                    last_bracket = response.rfind(']', 0, last_brace + 1)
                    if last_bracket > 0:
                        response = response[:last_bracket + 1] + '}'
            
            return response.strip()
        except Exception as e:
            print(f"[DEBUG] JSON fix failed: {e}")
            return response
    
    def validate_blanks(self, blanks: List[Dict], original_text: str) -> List[Dict]:
        """Validate blank data"""
        words = original_text.split()
        valid_blanks = []
        
        for blank in blanks:
            position = blank.get('position', -1)
            word = blank.get('word', '').strip()
            
            # Validate position and word match
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
        """Call AI service"""
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
                        "content": "You are a professional multilingual learning assistant specializing in creating high-quality listening fill-in-the-blank exercises. Please ensure you return complete and valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,  # Increase token limit to support batch processing
                "temperature": 0.1,  # Reduce randomness, improve JSON format stability
                "response_format": {"type": "json_object"}  # Force JSON format output
            }
            
            # Add retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    timeout = self.ai_config.get('timeout', 60)  # Increase timeout
                    response = requests.post(
                        self.ai_config['api_url'],
                        json=data,
                        headers=headers,
                        timeout=timeout
                    )
                    break  # Success, exit retry loop
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    print(f"[DEBUG] API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        raise  # Last attempt failed, raise exception
                    import time
                    time.sleep(2)  # Wait 2 seconds before retry
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()
            else:
                print(f"AI service returned error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Calling AI service failed: {e}")
        
        return None
    
    def test_json_fix(self):
        """Test JSON fix functionality"""
        test_response = '''{
    "exercises": ["
        {
            "sentence_index": 1,"
            "blanks": ["
                {
                    "position": 1,"
                    "word": "diferencia","
                    "hint": "noun, first letter d",
                    "difficulty": "medium"
                }
            ]
        }
    ]
}'''
        print("[DEBUG] Testing JSON fix functionality")
        print(f"Original response: {test_response}")
        fixed = self._fix_json_format(test_response)
        print(f"Fixed response: {fixed}")
        
        try:
            import json
            data = json.loads(fixed)
            print("[DEBUG] JSON fix successful!")
            return True
        except Exception as e:
            print(f"[DEBUG] JSON fix failed: {e}")
            return False
    
    def parse_ai_response(self, response: str, original_text: str) -> List[Dict]:
        """Parse AI response"""
        try:
            # Try to parse JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response)
            blanks = data.get('blanks', [])
            
            # Validate and clean data
            words = original_text.split()
            valid_blanks = []
            
            for blank in blanks:
                position = blank.get('position', -1)
                word = blank.get('word', '').strip()
                
                # Validate position and word match
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
            print(f"JSON parsing failed: {e}")
            print(f"AI response content: {response}")
            
            # If JSON parsing fails, try simple text parsing
            return self.fallback_parsing(response, original_text)
        
        except Exception as e:
            print(f"Parsing AI response failed: {e}")
            return []
    
    def fallback_parsing(self, response: str, original_text: str) -> List[Dict]:
        """Fallback parsing method"""
        try:
            words = original_text.split()
            # Simple fallback: randomly select 1-2 words
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
            print(f"Fallback parsing also failed: {e}")
            return []

class AIExerciseThread(QThread):
    """AI exercise generation thread"""
    
    # Signal definition
    generation_started = Signal()
    generation_finished = Signal(bool, str, list)
    progress_updated = Signal(int)
    
    def __init__(self, subtitles: List, exercise_config: Dict):
        super().__init__()
        self.subtitles = subtitles
        self.exercise_config = exercise_config
        self.generator = AIExerciseGenerator()
        
        # Connect signals
        self.generator.generation_started.connect(self.generation_started.emit)
        self.generator.generation_finished.connect(self.generation_finished.emit)
        self.generator.progress_updated.connect(self.progress_updated.emit)
    
    def run(self):
        """Run AI generation"""
        self.generator.generate_exercises(self.subtitles, self.exercise_config)
