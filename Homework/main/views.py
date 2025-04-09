from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import Question, Tag, User, Answer
from .forms import AskForm, AnswerForm
from django.shortcuts import get_object_or_404
from .forms import LoginForm, SignUpForm
import logging
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

data = {
    'questions': [
        {
            'id': 1,
            'title': 'Как создать веб-приложение на Django?',
            'text': 'Я хочу узнать, как создать простое веб-приложение на Django. С чего начать?',
            'author': {
                'username': 'user123',
                'avatar': 'path/to/avatar.jpg'
            },
            'tags': [
                {'title': 'Python'},
                {'title': 'Django'}
            ],
            'created_at': '2 часа назад'
        }
    ],
    'answers': [
        {
            'author': {
                'username': 'expert456',
                'avatar': 'path/to/expert_avatar.jpg'
            },
            'text': 'Для начала установите Django с помощью pip.',
            'created_at': '1 час назад'
        },
        {
            'author': {
                'username': 'dev789',
                'avatar': 'path/to/dev_avatar.jpg'
            },
            'text': 'Помните, что вам нужно создать проект с помощью команды django-admin startproject.',
            'created_at': '30 минут назад'
        }
    ]
}




def index(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    questions = Question.objects.all().select_related('author').prefetch_related('tags')
    context = {
        'questions': questions,
        'popular_tags': popular_tags,
        'best_members': best_members,
    }
    return render(request, 'main/index.html', context)

def question(request, question_id):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    question = get_object_or_404(Question, pk=question_id)
    answers = Answer.objects.filter(question=question)
    return render(request, 'main/question.html',
                  {
                      'question': question,
                      'answers': answers,
                      'popular_tags': popular_tags,
                      'best_members': best_members,
                      'count_ans': len(answers)
                  })

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

    return render(request, 'main/ask.html',
                  {
                      'form': form,
                      'popular_tags': popular_tags,
                      'best_members': best_members,
                  })

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
    return render(request, 'main/login.html',
                  {
                      'form': form,
                      'popular_tags': popular_tags,
                      'best_members': best_members,
                  })

@login_required
def settings(request):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    if request.method == 'POST':
        user = request.user
        user.nickname = request.POST.get('nickname', user.nickname)
        user.email = request.POST.get('email', user.email)

        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        user.save()
        return redirect('settings')

    return render(request, 'main/settings.html', {
        'popular_tags': popular_tags,
        'best_members': best_members,
    })

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
    return render(request, 'main/signup.html',
                  {
                      'form': form,
                      'popular_tags': popular_tags,
                      'best_members': best_members,
                  })

def logout_view(request):
    logout(request)
    return redirect('index')


def tag(request, tag_name):
    popular_tags = Tag.objects.popular_tags()
    best_members = User.objects.best_members()
    tag = get_object_or_404(Tag, title=tag_name)
    questions = Question.objects.filter(tags=tag)

    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/tag.html', {
        'tag': tag,
        'questions': page_obj,
        'popular_tags': popular_tags,
        'best_members': best_members,
    })

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

    return render(request, 'main/settings.html', {
        'popular_tags': popular_tags,
        'best_members': best_members,
        'user': user
    })