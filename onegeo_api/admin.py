from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Analyzer
from .models import Context
from .models import Filter
from .models import Resource
from .models import SearchModel
from .models import Source
from .models import Tokenizer
# from .models import Task

admin.site.unregister(Group)


@admin.register(Analyzer)
class AnalyzerAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


@admin.register(Context)
class ContextAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


@admin.register(Filter)
class FilterAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


@admin.register(Tokenizer)
class TokenizerAdmin(admin.ModelAdmin):
    list_display = ['name']
    ordering = ['name']


# @admin.register(Task)
# class TaskAdmin(admin.ModelAdmin):
#     list_display = ['start_date', 'success']
#     ordering = ['start_date']


@admin.register(SearchModel)
class SearchModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    ordering = ['name']
