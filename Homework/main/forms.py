from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Question, Tag, Answer


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    nickname = forms.CharField(required=True, label='Никнейм')
    avatar = forms.ImageField(required=False, label='Аватар', widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'nickname', 'password1', 'password2', 'avatar')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email



class LoginForm(forms.Form):
    username = forms.CharField(label='Логин')
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')


class AskForm(forms.ModelForm):
    tags = forms.CharField(required=False, help_text='Введите теги через запятую')

    class Meta:
        model = Question
        fields = ['title', 'text']

    def save(self, user, commit=True):
        question = super().save(commit=False)
        question.author = user

        if commit:
            question.save()
            self.process_tags(question)

        return question

    def process_tags(self, question):
        tags = self.cleaned_data.get('tags', '')
        if tags:
            tags_list = [t.strip() for t in tags.split(',') if t.strip()]
            for tag_name in tags_list:
                tag, _ = Tag.objects.get_or_create(title=tag_name)
                question.tags.add(tag)


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text']

    def save(self, user, question, commit=True):
        answer = super().save(commit=False)
        answer.author = user
        answer.question = question

        if commit:
            answer.save()

        return answer