from django.conf.urls import url

from onegeo_api.views.action import ActionView
from onegeo_api.views.action import AliasView
from onegeo_api.views.context import ContextIDView
from onegeo_api.views.context import ContextView
from onegeo_api.views.context import ContextIDTaskView
from onegeo_api.views.context import ContextIDTaskIDView
from onegeo_api.views.main import Directories, SupportedModes
from onegeo_api.views.resource import ResourceView, ResourceIDView
from onegeo_api.views.search_model import SearchModelIDView, SearchModelView, SearchView
from onegeo_api.views.source import SourceView, SourceIDView
from onegeo_api.views.task import TaskIDView
from onegeo_api.views.task import TaskView
from onegeo_api.views.filter import TokenFilterIDView
from onegeo_api.views.filter import TokenFilterView
from onegeo_api.views.tokenizer import TokenizerIDView
from onegeo_api.views.tokenizer import TokenizerView

# app_name = 'api'


urlpatterns = [
    url(r'^action/?$', ActionView.as_view(), name="action"),
    url(r'^indexes/(\S+)/tasks/?$', ContextIDTaskView.as_view(), name="context_detail_task_view_list"),
    url(r'^indexes/(\S+)/tasks/(\d+)/?$', ContextIDTaskIDView.as_view(), name="context_detail_task_view_detail"),
    url(r'^indexes/(\S+)/?$', ContextIDView.as_view(), name="context_detail"),
    url(r'^indexes/?$', ContextView.as_view(), name="context_list"),
    url(r'^services/(\S+)/search/?$', SearchView.as_view(), name="seamod_detail_search"),
    url(r'^services/(\S+)/?$', SearchModelIDView.as_view(), name="seamod_detail"),
    url(r'^services/?$', SearchModelView.as_view(), name="seamod_list"),
    url(r'^sources/(\S+)/resources/(\S+)/?$', ResourceIDView.as_view(), name="source_detail_resource_detail"),
    url(r'^sources/(\S+)/resources/?$', ResourceView.as_view(), name="source_detail_resource"),
    url(r'^sources/(\S+)/?$', SourceIDView.as_view(), name="source_detail"),
    url(r'^sources/?$', SourceView.as_view(), name="source_list"),
    url(r'^sources_directories/?$', Directories.as_view(), name="directories"),
    url(r'^supported_modes/?$', SupportedModes.as_view(), name="modes"),
    url(r'^tasks/(\d+)/?$', TaskIDView.as_view(), name="task_detail"),
    url(r'^tasks/?$', TaskView.as_view(), name="task_list"),
    url(r'^tokenfilters/(\S+)/?$', TokenFilterIDView.as_view()),
    url(r'^tokenfilters/?$', TokenFilterView.as_view()),
    url(r'^tokenizers/(\S+)/?$', TokenizerIDView.as_view()),
    url(r'^tokenizers/?$', TokenizerView.as_view()),
    url(r'^alias/(\S+)/?$', AliasView.as_view(), name="instance_alias")
    ]
