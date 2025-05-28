from django.core.management.base import BaseCommand
from main.models import Question


class Command(BaseCommand):
    help = 'Update likes/dislikes counters'

    def handle(self, *args, **options):
        batch_size = 1000
        questions = Question.objects.all()
        total = questions.count()

        for i in range(0, total, batch_size):
            batch = questions[i:i + batch_size]
            for question in batch:
                question.likes_count = question.likes.count()
                question.dislikes_count = question.dislikes.count()

            Question.objects.bulk_update(
                batch,
                ['likes_count', 'dislikes_count'],
                batch_size
            )
            self.stdout.write(f"Updated {min(i + batch_size, total)}/{total} questions")

        self.stdout.write(self.style.SUCCESS("Counters updated successfully"))