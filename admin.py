from django.contrib import admin

from .models import Source, Resource, Context, Filter, Analyzer

admin.site.register(Source)
admin.site.register(Resource)
admin.site.register(Context)
admin.site.register(Filter)
admin.site.register(Analyzer)