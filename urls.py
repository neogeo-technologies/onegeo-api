from django.conf.urls import url

from .views.action import ActionView
from .views.analyzer import AnalyzerIDView, AnalyzerView
from .views.context import ContextIDView, ContextView, \
                           ContextIDTaskView, ContextIDTaskIDView
from .views.main import Directories, SupportedModes
from .views.resource import ResourceView, ResourceIDView
from .views.search_model import SearchModelIDView, SearchModelView, SearchView
from .views.source import SourceView, SourceIDView
from .views.task import TaskIDView, TaskView
from .views.tokenizer import TokenizerIDView, TokenizerView
from .views.token_filter import TokenFilterIDView, TokenFilterView


app_name = 'api'


urlpatterns = [
    url(r'^action/?$', ActionView.as_view()),
    url(r'^analyzers/(\S+)?$', AnalyzerIDView.as_view()),
    url(r'^analyzers/?$', AnalyzerView.as_view()),
    url(r'^contexts/(\d+)/tasks/?$', ContextIDTaskView.as_view()),
    url(r'^contexts/(\d+)/tasks/(\d+)/?$', ContextIDTaskIDView.as_view()),
    url(r'^contexts/(\d+)/?$', ContextIDView.as_view()),
    url(r'^contexts/?$', ContextView.as_view()),
    url(r'^filters/(\S+)/?$', TokenFilterIDView.as_view()),
    url(r'^filters/?$', TokenFilterView.as_view()),
    url(r'^models/(\S+)/search/?$', SearchView.as_view()),
    url(r'^models/(\S+)/?$', SearchModelIDView.as_view()),
    url(r'^models/?$', SearchModelView.as_view()),
    url(r'^sources/(\d+)/resources/(\d+)/?$', ResourceIDView.as_view()),
    url(r'^sources/(\d+)/resources/?$', ResourceView.as_view()),
    url(r'^sources/(\d+)/?$', SourceIDView.as_view()),
    url(r'^sources/?$', SourceView.as_view()),
    url(r'^sources_directories/?$', Directories.as_view()),
    url(r'^supported_modes/?$', SupportedModes.as_view()),
    url(r'^tasks/(\d+)/?$', TaskIDView.as_view()),
    url(r'^tasks/?$', TaskView.as_view()),
    url(r'^tokenizers/(\S+)?$', TokenizerIDView.as_view()),
    url(r'^tokenizers/?$', TokenizerView.as_view()),
]
