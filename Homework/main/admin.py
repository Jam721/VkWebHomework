from django.contrib import admin
from .models import User, Question, Tag, Answer

admin.site.register(User)
admin.site.register(Question)
admin.site.register(Tag)
admin.site.register(Answer)