from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from main.models import User, Tag, Question, Answer
import random
import time
import math
from datetime import timedelta


class Command(BaseCommand):
    help = 'Fills the database with test data based on the ratio'

    def add_arguments(self, parser):
        parser.add_argument('ratio', type=int, help='Fill ratio coefficient')

    def handle(self, *args, **options):
        ratio = options['ratio']
        start_time = time.time()

        # Создаем пользователей
        self.stdout.write(f"Creating {ratio} users...")
        users = self.create_users(ratio)

        # Создаем теги
        self.stdout.write(f"Creating {ratio} tags...")
        tags = self.create_tags(ratio)

        # Создаем вопросы
        self.stdout.write(f"Creating {ratio * 10} questions...")
        questions = self.create_questions(ratio, users, tags)

        # Создаем ответы
        self.stdout.write(f"Creating {ratio * 100} answers...")
        self.create_answers(ratio, users, questions)

        # Создаем оценки
        self.stdout.write(f"Creating {ratio * 200} ratings...")
        self.create_ratings(ratio, users, questions)

        # Обновляем счетчики
        self.stdout.write("Updating counters...")
        self.update_counters(tags, questions)

        total_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Successfully filled database in {total_time:.2f} seconds"
        ))

    def create_users(self, ratio):
        users = []
        for i in range(ratio):
            user = User(
                username=f'user_{i}',
                email=f'user_{i}@example.com',
                nickname=f'nickname_{i}',
            )
            user.set_password('password123')
            users.append(user)
        return User.objects.bulk_create(users)

    def create_tags(self, ratio):
        tags = []
        for i in range(ratio):
            tags.append(Tag(title=f'tag_{i}'))
        return Tag.objects.bulk_create(tags)

    def create_questions(self, ratio, users, tags):
        batch_size = 5000
        total = ratio * 10
        questions = []

        for i in range(total):
            author = random.choice(users)
            question = Question(
                title=f'Question {i}',
                text=f'Text of question {i}',
                author=author,
                created_at=timezone.now() - timedelta(days=random.randint(0, 365)),
            )
            questions.append(question)

        # Создаем вопросы пакетами
        created_questions = []
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]
            created_questions.extend(Question.objects.bulk_create(batch))

        # Добавляем теги к вопросам
        self.add_tags_to_questions(created_questions, tags)
        return created_questions

    def add_tags_to_questions(self, questions, tags):
        question_tags = []
        through_model = Question.tags.through

        for question in questions:
            selected_tags = random.sample(list(tags), min(5, len(tags)))
            for tag in selected_tags:
                question_tags.append(through_model(question_id=question.id, tag_id=tag.id))

        # Вставляем связи пакетами
        batch_size = 10000
        for i in range(0, len(question_tags), batch_size):
            through_model.objects.bulk_create(question_tags[i:i + batch_size])

    def create_answers(self, ratio, users, questions):
        batch_size = 10000
        total = ratio * 100
        answers = []

        for i in range(total):
            question = random.choice(questions)
            author = random.choice(users)
            answer = Answer(
                text=f'Answer {i} to question {question.id}',
                author=author,
                question=question,
                created_at=timezone.now() - timedelta(days=random.randint(0, 365)),
                is_correct=random.choice([True, False]),
            )
            answers.append(answer)

        # Создаем ответы пакетами
        for i in range(0, len(answers), batch_size):
            Answer.objects.bulk_create(answers[i:i + batch_size])

    def create_ratings(self, ratio, users, questions):
        total_ratings = ratio * 200
        ratings_set = set()
        likes_list = []
        dislikes_list = []

        # Генерируем уникальные оценки
        while len(ratings_set) < total_ratings:
            user = random.choice(users)
            question = random.choice(questions)
            key = (user.id, question.id)

            if key not in ratings_set:
                ratings_set.add(key)
                if random.choice([True, False]):
                    likes_list.append(question.likes.through(user_id=user.id, question_id=question.id))
                else:
                    dislikes_list.append(question.dislikes.through(user_id=user.id, question_id=question.id))

        # Создаем лайки и дизлайки
        batch_size = 10000
        self.create_bulk_ratings(likes_list, batch_size)
        self.create_bulk_ratings(dislikes_list, batch_size)

    def create_bulk_ratings(self, ratings, batch_size):
        for i in range(0, len(ratings), batch_size):
            batch = ratings[i:i + batch_size]
            model = batch[0].__class__ if batch else None
            if model:
                model.objects.bulk_create(batch)

    def update_counters(self, tags, questions):
        # Обновляем счетчики тегов
        for tag in tags:
            tag.num_questions = tag.questions.count()
            tag.save()

        # Обновляем счетчики вопросов
        for question in questions:
            question.likes_count = question.likes.count()
            question.dislikes_count = question.dislikes.count()
            question.save()