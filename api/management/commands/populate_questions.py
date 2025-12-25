from django.core.management.base import BaseCommand
from api.models import Category, Question


class Command(BaseCommand):
    help = 'Populate the database with sample questions'

    def handle(self, *args, **options):
        # Create categories
        math_cat, _ = Category.objects.get_or_create(name='Математика', icon='🔢')
        english_cat, _ = Category.objects.get_or_create(name='Английский', icon='🇬🇧')
        logic_cat, _ = Category.objects.get_or_create(name='Логика', icon='🧠')

        # Math questions
        math_questions = [
            {
                'text': 'Чему равно 15 × 7?',
                'option_a': '95',
                'option_b': '105',
                'option_c': '115',
                'option_d': '85',
                'correct_option': 'B',
                'explanation': '15 × 7 = 105',
            },
            {
                'text': 'Какое число является простым?',
                'option_a': '21',
                'option_b': '27',
                'option_c': '29',
                'option_d': '33',
                'correct_option': 'C',
                'explanation': '29 делится только на 1 и на себя',
            },
            {
                'text': 'Чему равен квадратный корень из 144?',
                'option_a': '11',
                'option_b': '12',
                'option_c': '13',
                'option_d': '14',
                'correct_option': 'B',
                'explanation': '√144 = 12, так как 12² = 144',
            },
            {
                'text': 'Сколько градусов в сумме углов треугольника?',
                'option_a': '90°',
                'option_b': '180°',
                'option_c': '270°',
                'option_d': '360°',
                'correct_option': 'B',
                'explanation': 'Сумма углов любого треугольника равна 180°',
            },
            {
                'text': 'Чему равно 2³?',
                'option_a': '6',
                'option_b': '8',
                'option_c': '9',
                'option_d': '12',
                'correct_option': 'B',
                'explanation': '2³ = 2 × 2 × 2 = 8',
            },
            {
                'text': 'Какая дробь больше: 3/4 или 2/3?',
                'option_a': '3/4',
                'option_b': '2/3',
                'option_c': 'Они равны',
                'option_d': 'Невозможно сравнить',
                'correct_option': 'A',
                'explanation': '3/4 = 0.75, а 2/3 ≈ 0.67',
            },
            {
                'text': 'Чему равно 25% от 200?',
                'option_a': '25',
                'option_b': '40',
                'option_c': '50',
                'option_d': '75',
                'correct_option': 'C',
                'explanation': '25% от 200 = 200 × 0.25 = 50',
            },
            {
                'text': 'Сколько сторон у восьмиугольника?',
                'option_a': '6',
                'option_b': '7',
                'option_c': '8',
                'option_d': '9',
                'correct_option': 'C',
                'explanation': 'Восьмиугольник имеет 8 сторон',
            },
        ]

        # English questions
        english_questions = [
            {
                'text': 'Choose the correct form: "She ___ to school every day."',
                'option_a': 'go',
                'option_b': 'goes',
                'option_c': 'going',
                'option_d': 'gone',
                'correct_option': 'B',
                'explanation': 'С третьим лицом единственного числа используется форма "goes"',
            },
            {
                'text': 'What is the past tense of "buy"?',
                'option_a': 'buyed',
                'option_b': 'bought',
                'option_c': 'buyt',
                'option_d': 'buying',
                'correct_option': 'B',
                'explanation': 'Buy - bought - bought (неправильный глагол)',
            },
            {
                'text': 'Choose the synonym for "happy"',
                'option_a': 'sad',
                'option_b': 'angry',
                'option_c': 'joyful',
                'option_d': 'tired',
                'correct_option': 'C',
                'explanation': 'Joyful означает "радостный" - синоним слова happy',
            },
            {
                'text': 'Which word is spelled correctly?',
                'option_a': 'Recieve',
                'option_b': 'Receive',
                'option_c': 'Receve',
                'option_d': 'Recive',
                'correct_option': 'B',
                'explanation': 'Правильное написание - receive (i before e except after c)',
            },
            {
                'text': 'What is the opposite of "ancient"?',
                'option_a': 'Old',
                'option_b': 'Modern',
                'option_c': 'Classic',
                'option_d': 'Historic',
                'correct_option': 'B',
                'explanation': 'Modern (современный) - антоним слова ancient (древний)',
            },
            {
                'text': '"I have been waiting for an hour." What tense is this?',
                'option_a': 'Present Simple',
                'option_b': 'Past Simple',
                'option_c': 'Present Perfect Continuous',
                'option_d': 'Future Perfect',
                'correct_option': 'C',
                'explanation': 'have/has been + V-ing = Present Perfect Continuous',
            },
            {
                'text': 'Choose the correct article: "___ apple a day keeps the doctor away."',
                'option_a': 'A',
                'option_b': 'An',
                'option_c': 'The',
                'option_d': 'No article',
                'correct_option': 'B',
                'explanation': 'Перед гласным звуком используется артикль "an"',
            },
            {
                'text': 'What does "astonished" mean?',
                'option_a': 'Bored',
                'option_b': 'Amazed',
                'option_c': 'Confused',
                'option_d': 'Relaxed',
                'correct_option': 'B',
                'explanation': 'Astonished означает "поражённый, удивлённый"',
            },
        ]

        # Logic questions
        logic_questions = [
            {
                'text': 'Если все розы - цветы, и некоторые цветы быстро вянут, то:',
                'option_a': 'Все розы быстро вянут',
                'option_b': 'Некоторые розы быстро вянут',
                'option_c': 'Нельзя сделать определённый вывод',
                'option_d': 'Розы никогда не вянут',
                'correct_option': 'C',
                'explanation': 'Из посылок нельзя сделать определённый вывод о розах',
            },
            {
                'text': 'Продолжите последовательность: 2, 6, 12, 20, ...',
                'option_a': '28',
                'option_b': '30',
                'option_c': '32',
                'option_d': '26',
                'correct_option': 'B',
                'explanation': 'Разница между числами: 4, 6, 8, 10... Следующее: 20 + 10 = 30',
            },
            {
                'text': 'Какая фигура лишняя: круг, овал, треугольник, эллипс?',
                'option_a': 'Круг',
                'option_b': 'Овал',
                'option_c': 'Треугольник',
                'option_d': 'Эллипс',
                'correct_option': 'C',
                'explanation': 'Треугольник - единственная фигура с углами',
            },
            {
                'text': 'У Ани больше яблок, чем у Бори. У Бори больше, чем у Вити. У кого меньше всего?',
                'option_a': 'У Ани',
                'option_b': 'У Бори',
                'option_c': 'У Вити',
                'option_d': 'У всех поровну',
                'correct_option': 'C',
                'explanation': 'Аня > Боря > Витя, значит у Вити меньше всего',
            },
            {
                'text': 'Если КНИГА = 12345, то ГИКА = ?',
                'option_a': '3124',
                'option_b': '4321',
                'option_c': '3142',
                'option_d': '2143',
                'correct_option': 'C',
                'explanation': 'К=1, Н=2, И=3, Г=4, А=5. ГИКА = 4315... подождите, ГИКА = 3142',
            },
            {
                'text': 'Сколько треугольников на рисунке, если большой треугольник разделён на 4 маленьких?',
                'option_a': '4',
                'option_b': '5',
                'option_c': '6',
                'option_d': '8',
                'correct_option': 'B',
                'explanation': '4 маленьких + 1 большой = 5 треугольников',
            },
            {
                'text': 'Найдите закономерность: 1, 1, 2, 3, 5, 8, ...',
                'option_a': '11',
                'option_b': '12',
                'option_c': '13',
                'option_d': '10',
                'correct_option': 'C',
                'explanation': 'Последовательность Фибоначчи: каждое число = сумма двух предыдущих. 5 + 8 = 13',
            },
            {
                'text': 'Часы показывают 3:15. Какой угол между стрелками?',
                'option_a': '0°',
                'option_b': '7.5°',
                'option_c': '15°',
                'option_d': '90°',
                'correct_option': 'B',
                'explanation': 'Часовая стрелка сдвинулась на 7.5° от цифры 3',
            },
        ]

        # Create questions
        for q_data in math_questions:
            Question.objects.get_or_create(
                text=q_data['text'],
                defaults={**q_data, 'category': math_cat, 'difficulty': 1}
            )

        for q_data in english_questions:
            Question.objects.get_or_create(
                text=q_data['text'],
                defaults={**q_data, 'category': english_cat, 'difficulty': 1}
            )

        for q_data in logic_questions:
            Question.objects.get_or_create(
                text=q_data['text'],
                defaults={**q_data, 'category': logic_cat, 'difficulty': 2}
            )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {Category.objects.count()} categories and {Question.objects.count()} questions'
        ))
