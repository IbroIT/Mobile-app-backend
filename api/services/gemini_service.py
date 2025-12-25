import google.generativeai as genai
import json
import re
from typing import Optional
from django.conf import settings


class GeminiService:
    """Service for generating questions using Gemini AI"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
    
    def generate_questions(
        self,
        category: str,
        count: int = 5,
        difficulty: str = 'medium',
        language: str = 'ru'
    ) -> list[dict]:
        """Generate quiz questions using Gemini AI"""
        
        if not self.model:
            raise ValueError("Gemini API key not configured")
        
        difficulty_map = {
            'easy': 'простые, для начинающих',
            'medium': 'средней сложности',
            'hard': 'сложные, для экспертов'
        }
        
        category_prompts = {
            'math': 'математика (арифметика, алгебра, геометрия)',
            'english': 'английский язык (грамматика, словарный запас, идиомы)',
            'logic': 'логика и головоломки',
            'science': 'наука (физика, химия, биология)',
            'history': 'история',
            'geography': 'география',
            'general': 'общие знания',
        }
        
        category_text = category_prompts.get(category, category)
        difficulty_text = difficulty_map.get(difficulty, difficulty_map['medium'])
        
        lang_instruction = "на русском языке" if language == 'ru' else "in English"
        
        prompt = f"""Сгенерируй {count} уникальных вопросов для викторины {lang_instruction}.

Категория: {category_text}
Сложность: {difficulty_text}

Требования:
1. Каждый вопрос должен иметь ровно 4 варианта ответа (A, B, C, D)
2. Только один вариант должен быть правильным
3. Вопросы должны быть разнообразными и интересными
4. Добавь краткое объяснение правильного ответа

Верни ответ ТОЛЬКО в формате JSON массива, без дополнительного текста:
[
  {{
    "text": "Текст вопроса?",
    "option_a": "Первый вариант",
    "option_b": "Второй вариант",
    "option_c": "Третий вариант",
    "option_d": "Четвёртый вариант",
    "correct_option": "A",
    "explanation": "Объяснение правильного ответа"
  }}
]

Верни только JSON без markdown разметки."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            
            questions = json.loads(text)
            
            # Validate structure
            validated_questions = []
            for q in questions:
                if all(key in q for key in ['text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option']):
                    # Ensure correct_option is uppercase
                    q['correct_option'] = q['correct_option'].upper()
                    if q['correct_option'] in ['A', 'B', 'C', 'D']:
                        validated_questions.append(q)
            
            return validated_questions
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {text[:500]}")
            return []
        except Exception as e:
            print(f"Gemini API error: {e}")
            return []
    
    def generate_single_question(
        self,
        category: str,
        difficulty: str = 'medium',
        language: str = 'ru',
        exclude_texts: list[str] = None
    ) -> Optional[dict]:
        """Generate a single unique question"""
        
        if not self.model:
            raise ValueError("Gemini API key not configured")
        
        exclude_instruction = ""
        if exclude_texts:
            exclude_instruction = f"\n\nНЕ используй следующие вопросы (они уже были):\n" + "\n".join(f"- {t}" for t in exclude_texts[:10])
        
        questions = self.generate_questions(category, count=1, difficulty=difficulty, language=language)
        
        if questions:
            return questions[0]
        return None


# Global instance
gemini_service = GeminiService()
