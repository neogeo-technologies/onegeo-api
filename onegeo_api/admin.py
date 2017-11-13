from django.contrib import admin
from onegeo_api.models import Analyzer
from onegeo_api.models import Context
from onegeo_api.models import Filter
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.models import Tokenizer


admin.site.register(Source)
admin.site.register(Resource)
admin.site.register(Context)
admin.site.register(Filter)
admin.site.register(Analyzer)
admin.site.register(Tokenizer)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'success']
    ordering = ['start_date']


@admin.register(SearchModel)
class SearchModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    ordering = ['name']
