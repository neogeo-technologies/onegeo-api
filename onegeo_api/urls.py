from django.conf.urls import url
from onegeo_api.views.action import ActionView
from onegeo_api.views.analyzer import AnalyzerIDView
from onegeo_api.views.analyzer import AnalyzerView
from onegeo_api.views.context import ContextIDTaskIDView
from onegeo_api.views.context import ContextIDTaskView
from onegeo_api.views.context import ContextIDView
from onegeo_api.views.context import ContextView
from onegeo_api.views.main import Directories
from onegeo_api.views.main import SupportedModes
from onegeo_api.views.resource import ResourceIDView
from onegeo_api.views.resource import ResourceView
from onegeo_api.views.search_model import SearchModelIDView
from onegeo_api.views.search_model import SearchModelView
from onegeo_api.views.search_model import SearchView
from onegeo_api.views.source import SourceIDView
from onegeo_api.views.source import SourceView
from onegeo_api.views.task import TaskIDView
from onegeo_api.views.task import TaskView
from onegeo_api.views.token_filter import TokenFilterIDView
from onegeo_api.views.token_filter import TokenFilterView
from onegeo_api.views.tokenizer import TokenizerIDView
from onegeo_api.views.tokenizer import TokenizerView


app_name = 'api'


urlpatterns = [
    url(r'^action/?$', ActionView.as_view()),
    url(r'^analyzers/(\S+)/?$', AnalyzerIDView.as_view()),
    url(r'^analyzers/?$', AnalyzerView.as_view()),
    url(r'^indices/(\d+)/tasks/?$', ContextIDTaskView.as_view()),
    url(r'^indices/(\d+)/tasks/(\d+)/?$', ContextIDTaskIDView.as_view()),
    url(r'^indices/(\d+)/?$', ContextIDView.as_view()),
    url(r'^indices/?$', ContextView.as_view()),
    url(r'^tokenfilters/(\S+)/?$', TokenFilterIDView.as_view()),
    url(r'^tokenfilters/?$', TokenFilterView.as_view()),
    url(r'^profiles/(\S+)/search/?$', SearchView.as_view()),
    url(r'^profiles/(\S+)/?$', SearchModelIDView.as_view()),
    url(r'^profiles/?$', SearchModelView.as_view()),
    url(r'^sources/(\d+)/resources/(\d+)/?$', ResourceIDView.as_view()),
    url(r'^sources/(\d+)/resources/?$', ResourceView.as_view()),
    url(r'^sources/(\d+)/?$', SourceIDView.as_view()),
    url(r'^sources/?$', SourceView.as_view()),
    url(r'^sources_directories/?$', Directories.as_view()),
    url(r'^supported_modes/?$', SupportedModes.as_view()),
    url(r'^tasks/(\d+)/?$', TaskIDView.as_view()),
    url(r'^tasks/?$', TaskView.as_view()),
    url(r'^tokenizers/(\S+)/?$', TokenizerIDView.as_view()),
    url(r'^tokenizers/?$', TokenizerView.as_view()),
]
