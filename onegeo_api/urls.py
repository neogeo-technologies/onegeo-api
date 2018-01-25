from django.conf.urls import url

from onegeo_api.views.action import Action
from onegeo_api.views.action import AliasDetail
from onegeo_api.views.action import Bulk
from onegeo_api.views.analyzer import AnalyzersDetail
from onegeo_api.views.analyzer import AnalyzersList
from onegeo_api.views.index_profile import IndexProfilesDetail
from onegeo_api.views.index_profile import IndexProfilesList
from onegeo_api.views.index_profile import IndexProfilesTasksDetail
from onegeo_api.views.index_profile import IndexProfilesTasksList
from onegeo_api.views.filter import TokenFiltersDetail
from onegeo_api.views.filter import TokenFiltersList
from onegeo_api.views.main import Directories, SupportedModes
from onegeo_api.views.resource import ResourcesDetail
from onegeo_api.views.resource import ResourcesList
from onegeo_api.views.search_model import SearchModelsDetail
from onegeo_api.views.search_model import SearchModelsList
from onegeo_api.views.search_model import Search
from onegeo_api.views.source import SourcesList
from onegeo_api.views.source import SourcesDetail
from onegeo_api.views.task import TasksDetail
from onegeo_api.views.task import TasksList
from onegeo_api.views.tokenizer import TokenizersDetail
from onegeo_api.views.tokenizer import TokenizersList


app_name = 'onegeo_api'


urlpatterns = [
    url(r'^action/?$', Action.as_view(), name="action"),
    url(r'^analyzers/(?P<alias>\S+)/?$', AnalyzersDetail.as_view(), name="analyzers_detail"),
    url(r'^analyzers/?$', AnalyzersList.as_view(), name="analyzers_list"),
    url(r'^indexes/(\S+)/tasks/?$', IndexProfilesTasksList.as_view(), name="indexes_task_view_list"),
    url(r'^indexes/(\S+)/tasks/(\d+)/?$', IndexProfilesTasksDetail.as_view(), name="indexes_task_view_detail"),
    url(r'^indexes/(?P<alias>\S+)/?$', IndexProfilesDetail.as_view(), name="indexes_detail"),
    url(r'^indexes/?$', IndexProfilesList.as_view(), name="indexes_list"),
    url(r'^services/(?P<alias>\S+)/search/?$', Search.as_view(), name="seamod_detail_search"),
    url(r'^services/(?P<alias>\S+)/?$', SearchModelsDetail.as_view(), name="seamod_detail"),
    url(r'^services/?$', SearchModelsList.as_view(), name="seamod_list"),
    url(r'^sources/(?P<src_alias>\S+)/resources/(?P<rsrc_alias>\S+)/?$', ResourcesDetail.as_view(), name="resources_detail"),
    url(r'^sources/(?P<src_alias>\S+)/resources/?$', ResourcesList.as_view(), name="resources_list"),
    url(r'^sources/(?P<alias>\S+)/?$', SourcesDetail.as_view(), name="sources_detail"),
    url(r'^sources/?$', SourcesList.as_view(), name="sources_list"),
    url(r'^sources_directories/?$', Directories.as_view(), name="directories"),
    url(r'^supported_modes/?$', SupportedModes.as_view(), name="modes"),
    url(r'^tasks/(\d+)/?$', TasksDetail.as_view(), name="tasks_detail"),
    url(r'^tasks/?$', TasksList.as_view(), name="tasks_list"),
    url(r'^tokenfilters/(?P<alias>\S+)/?$', TokenFiltersDetail.as_view(), name="tokenfilters_detail"),
    url(r'^tokenfilters/?$', TokenFiltersList.as_view(), name="tokenfilters_list"),
    url(r'^tokenizers/(?P<alias>\S+)/?$', TokenizersDetail.as_view(), name="tokenizers_detail"),
    url(r'^tokenizers/?$', TokenizersList.as_view(), name="tokenizers_list"),
    url(r'^alias/(?P<alias>\S+)/?$', AliasDetail.as_view(), name="alias_search"),
    url(r'^bulk/?$', Bulk.as_view(), name="bulk")
    ]
