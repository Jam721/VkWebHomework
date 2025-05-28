from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from main.models import User, Tag
import time
import math


class Command(BaseCommand):
    help = 'Optimized database filler for 1 million records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1000000,
            help='Number of questions to create (default: 1000000)'
        )
        parser.add_argument(
            '--batch',
            type=int,
            default=5000,
            help='Batch size (default: 5000)'
        )

    def handle(self, *args, **options):
        total = options['count']
        batch_size = options['batch']

        # Создаем системного пользователя
        author = User.objects.first()
        if not author:
            author = User.objects.create(
                username='bulk_user',
                email='bulk@example.com',
                password='unused_password'
            )

        # Создаем теги
        tag_names = ['python', 'django', 'postgres', 'asyncio', 'debug']
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(title=name)
            tags.append(tag)
        tag_ids = [tag.id for tag in tags]

        start_time = time.time()
        self.stdout.write(f"Starting creation of {total} questions...")

        # Рассчитываем количество пакетов
        batches = math.ceil(total / batch_size)
        created = 0

        # Используем одно соединение для всех операций
        with connection.cursor() as cursor:
            try:
                # Временное отключение проверок
                cursor.execute("SET session_replication_role = 'replica';")
                cursor.execute("ALTER TABLE main_question DISABLE TRIGGER ALL;")
                cursor.execute("ALTER TABLE main_question_tags DISABLE TRIGGER ALL;")
            except Exception as e:
                self.stderr.write(f"Warning: Could not disable checks: {e}")

            try:
                for i in range(batches):
                    current_batch = min(batch_size, total - created)
                    values = []
                    timestamp = timezone.now().isoformat()

                    # Формируем значения для пакетной вставки
                    for j in range(current_batch):
                        num = created + j + 1
                        values.append(
                            f"('Question {num}', 'Auto generated content', "
                            f"{author.id}, '{timestamp}', 0, 0)"
                        )

                    # Вставляем вопросы
                    query = f"""
                        INSERT INTO main_question 
                        (title, text, author_id, created_at, likes_count, dislikes_count)
                        VALUES {','.join(values)}
                        RETURNING id
                    """
                    cursor.execute(query)

                    # Получаем ID вставленных вопросов
                    rows = cursor.fetchall()
                    question_ids = [row[0] for row in rows]

                    # Формируем связи с тегами
                    relations = []
                    for q_id in question_ids:
                        for tag_id in tag_ids:
                            relations.append(f"({q_id}, {tag_id})")

                    # Вставляем связи
                    if relations:
                        # Разбиваем на части для PostgreSQL
                        for k in range(0, len(relations), 1000):
                            chunk = relations[k:k + 1000]
                            cursor.execute(f"""
                                INSERT INTO main_question_tags (question_id, tag_id)
                                VALUES {','.join(chunk)}
                            """)

                    created += current_batch
                    elapsed = time.time() - start_time
                    per_second = created / elapsed if elapsed > 0 else 0

                    self.stdout.write(
                        f"Created {created}/{total} records "
                        f"({per_second:.2f} rec/sec) "
                        f"[Elapsed: {elapsed:.2f}s]"
                    )

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error: {e}"))
                connection.rollback()
                raise
            finally:
                # Всегда восстанавливаем состояние БД
                try:
                    cursor.execute("ALTER TABLE main_question ENABLE TRIGGER ALL;")
                    cursor.execute("ALTER TABLE main_question_tags ENABLE TRIGGER ALL;")
                    cursor.execute("SET session_replication_role = 'origin';")
                    cursor.execute("REINDEX TABLE main_question;")
                    cursor.execute("REINDEX TABLE main_question_tags;")
                except Exception as e:
                    self.stderr.write(f"Warning: Could not enable triggers: {e}")

        # Финализируем процесс
        total_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {total} questions "
            f"in {total_time:.2f} seconds "
            f"({total / total_time:.2f} rec/sec)"
        ))

        # Обновляем счетчики тегов
        self.stdout.write("Updating tag counters...")
        for tag in tags:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE main_tag
                    SET num_questions = (
                        SELECT COUNT(*) 
                        FROM main_question_tags 
                        WHERE tag_id = %s
                    )
                    WHERE id = %s
                """, [tag.id, tag.id])

        self.stdout.write(self.style.SUCCESS("All operations completed!"))