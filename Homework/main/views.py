from datetime import time

from django.core.cache import cache
from django.db import transaction, connection
from django.db.models import Count, Max, F
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from .models import Question, Tag, User, Answer
from .forms import AskForm, AnswerForm
from .forms import LoginForm, SignUpForm
import logging
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


def index(request):
    # Используем кэширование для популярных тегов и пользователей
    popular_tags = cache.get_or_set(
        'popular_tags',
        Tag.objects.popular_tags,
        300  # 5 минут кэширования
    )
    best_members = cache.get_or_set(
        'best_members',
        User.objects.best_members,
        300
    )
    # Убираем аннотации, используем предварительно рассчитанные поля
    questions = Question.objects.all() \
        .only('id', 'title', 'created_at', 'author_id', 'likes_count') \
        .select_related('author') \
        .prefetch_related('tags') \
        .order_by('-created_at')

    paginator = Paginator(questions, 20)  # Увеличиваем размер страницы
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'questions': page_obj,
        'popular_tags': popular_tags,
        'best_members': best_members,
        'title': 'New Questions'
    }
    return render(request, 'main/index.html', context)


def hot_questions(request):
    # Используем предварительно рассчитанное поле likes_count
    questions_list = Question.objects.all() \
        .only('id', 'title', 'created_at', 'author_id', 'likes_count') \
        .select_related('author') \
        .prefetch_related('tags') \
        .order_by('-likes_count', '-created_at')

    paginator = Paginator(questions_list, 20)  # Увеличиваем размер страницы
    page_number = request.GET.get('page')
    questions = paginator.get_page(page_number)

    popular_tags = cache.get_or_set('popular_tags', Tag.objects.popular_tags, 300)
    best_members = cache.get_or_set('best_members', User.objects.best_members, 300)

    return render(request, 'main/index.html', {
        'questions': questions,
        'popular_tags': popular_tags,
        'best_members': best_members,
        'title': 'Hot Questions',
    })


@login_required
@require_POST
@transaction.atomic  # Атомарная операция
def toggle_like(request):
    question_id = request.POST.get('id')
    question = get_object_or_404(Question, pk=question_id)
    user = request.user

    # Используем атомарное обновление счетчиков
    if question.likes.filter(id=user.id).exists():
        question.likes.remove(user)
        question.likes_count = F('likes_count') - 1
        liked = False
    else:
        question.likes.add(user)
        question.likes_count = F('likes_count') + 1
        # Убираем дизлайк если есть
        if question.dislikes.filter(id=user.id).exists():
            question.dislikes.remove(user)
            question.dislikes_count = F('dislikes_count') - 1
        liked = True

    question.save(update_fields=['likes_count', 'dislikes_count'])
    question.refresh_from_db()  # Обновляем объект

    return JsonResponse({
        'liked': liked,
        'total_likes': question.likes_count,
        'total_dislikes': question.dislikes_count
    })


@login_required
@require_POST
@transaction.atomic  # Атомарная операция
def toggle_dislike(request):
    question_id = request.POST.get('id')
    question = get_object_or_404(Question, pk=question_id)
    user = request.user

    if question.dislikes.filter(id=user.id).exists():
        question.dislikes.remove(user)
        question.dislikes_count = F('dislikes_count') - 1
        disliked = False
    else:
        question.dislikes.add(user)
        question.dislikes_count = F('dislikes_count') + 1
        # Убираем лайк если есть
        if question.likes.filter(id=user.id).exists():
            question.likes.remove(user)
            question.likes_count = F('likes_count') - 1
        disliked = True

    question.save(update_fields=['likes_count', 'dislikes_count'])
    question.refresh_from_db()  # Обновляем объект

    return JsonResponse({
        'disliked': disliked,
        'total_likes': question.likes_count,
        'total_dislikes': question.dislikes_count
    })


def question(request, question_id):
    # Используем предварительно рассчитанные поля
    me_question = get_object_or_404(
        Question.objects.select_related('author').prefetch_related('tags'),
        pk=question_id
    )

    # Оптимизируем запрос ответов
    answers = Answer.objects.filter(question=me_question) \
        .select_related('author') \
        .only('id', 'text', 'author_id', 'question_id', 'created_at')

    popular_tags = cache.get_or_set('popular_tags', Tag.objects.popular_tags, 300)
    best_members = cache.get_or_set('best_members', User.objects.best_members, 300)

    context = {
        'question': me_question,
        'answers': answers,
        'popular_tags': popular_tags,
        'best_members': best_members,
        'count_ans': answers.count(),
    }
    return render(request, 'main/question.html', context)


@login_required
def ask(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    if request.method == 'POST':
        form = AskForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.author = request.user
            question.save()

            tags = form.cleaned_data['tags']

            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            else:
                tags = [t.strip() for t in tags]

            for tag_name in tags:
                tag, _ = Tag.objects.get_or_create(title=tag_name)
                question.tags.add(tag)

            return redirect('index')
    else:
        form = AskForm()

    context = {
        'form': form,
        'popular_tags': popular_tags,
        'best_members': best_members,
    }

    return render(request, 'main/ask.html', context)

def login_view(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                return redirect('index')
            else:
                return render(request, 'main/login.html', {
                    'form': form,
                    'error': 'auth_error',
                })
    else:
        form = LoginForm()

    context = {
        'form': form,
        'popular_tags': popular_tags,
        'best_members': best_members,
    }
    return render(request, 'main/login.html', context)


def signup(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        else:
            error_type = 'email_exists' if form.errors.get('email') else 'form_invalid'
            return render(request, 'main/signup.html', {
                'form': form,
                'error': error_type,
            })
    else:
        form = SignUpForm()

    context = {
        'form': form,
        'popular_tags': popular_tags,
        'best_members': best_members,
    }
    return render(request, 'main/signup.html', context)

def logout_view(request):
    logout(request)
    return redirect('index')


def tag(request, tag_name):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    tag = get_object_or_404(Tag, title=tag_name)

    questions = Question.objects.filter(tags=tag)\
        .only('id', 'title', 'created_at', 'author_id')\
        .select_related('author')\
        .prefetch_related('tags')\
        .order_by('-created_at')

    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tag': tag,
        'questions': page_obj,
        'popular_tags': popular_tags,
        'best_members': best_members,
    }

    return render(request, 'main/tag.html', context)


@login_required
def answer(request, question_id):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    question = get_object_or_404(Question, pk=question_id)
    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.author = request.user
            answer.question = question
            answer.save()
            return redirect('question', question_id=question.id)
    return redirect('question', question_id=question.id)


@login_required
def settings(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    user = request.user

    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        user.nickname = request.POST.get('nickname', user.nickname)

        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        user.save()
        return redirect('settings')

    context = {
        'popular_tags': popular_tags,
        'best_members': best_members,
        'user': user
    }

    return render(request, 'main/settings.html', context)