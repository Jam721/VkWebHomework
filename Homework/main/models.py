from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.db.models import Count


class TagManager(models.Manager):
    def popular_tags(self):
        return self.annotate(
            num_questions=Count('questions')
        ).order_by('-num_questions')[:5]


class UserManager(BaseUserManager):
    def best_members(self):
        return self.annotate(
            num_questions=Count('questions'),
            num_answers=Count('answers')
        ).order_by('-num_questions', '-num_answers')[:5]

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='Email')
    nickname = models.CharField(max_length=50, unique=True, verbose_name='Никнейм')
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    objects = UserManager()

    def __str__(self):
        return self.username


class Tag(models.Model):
    title = models.CharField(max_length=50, unique=True)
    objects = TagManager()

    def __str__(self):
        return self.title


class Question(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='questions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Answer(models.Model):
    text = models.TextField(verbose_name='Текст ответа')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    is_correct = models.BooleanField(default=False, verbose_name='Правильный ответ')
    created_at = models.DateTimeField(auto_now_add=True)
