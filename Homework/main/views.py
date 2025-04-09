from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import Question, Tag, User, Answer
from .forms import AskForm, AnswerForm
from .forms import LoginForm, SignUpForm
import logging
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

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
    context = {
        'question': question,
        'answers': answers,
        'popular_tags': popular_tags,
        'best_members': best_members,
        'count_ans': len(answers)
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
    questions = Question.objects.filter(tags=tag)

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