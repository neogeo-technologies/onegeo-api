from django.contrib import admin

from .models import Source, Resource, Context, Filter, Analyzer, Tokenizer, SearchModel, Task

admin.site.register(Source)
admin.site.register(Resource)
admin.site.register(Context)
admin.site.register(Filter)
admin.site.register(Analyzer)
admin.site.register(Tokenizer)
admin.site.register(SearchModel)
admin.site.register(Task)
