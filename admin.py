from django.contrib import admin

from .models import Source, Resource, Context, Filter, Analyzer, Tokenizer, SearchModel, Task

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
