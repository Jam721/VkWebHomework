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
    tags = forms.CharField(
        label='Теги',
        help_text='Разделяйте теги запятыми',
        required=False
    )

    class Meta:
        model = Question
        fields = ['title', 'text']

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        return [t.strip() for t in tags.split(',') if t.strip()]


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 5})
        }