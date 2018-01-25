from django.contrib import admin
from django.contrib.auth.models import Group


from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source


admin.site.unregister(Group)


@admin.register(IndexProfile)
class IndexProfileAdmin(admin.ModelAdmin):
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


# @admin.register(Task)
# class TaskAdmin(admin.ModelAdmin):
#     list_display = ['start_date', 'success']
#     ordering = ['start_date']


@admin.register(SearchModel)
class SearchModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    ordering = ['name']
