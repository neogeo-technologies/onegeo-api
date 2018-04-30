# Copyright (c) 2017-2018 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from django.conf.urls import url
from onegeo_api.views.analyzer import AnalyzersDetail
from onegeo_api.views.analyzer import AnalyzersList
from onegeo_api.views.catalog import Catalog
from onegeo_api.views.filter import TokenFiltersDetail
from onegeo_api.views.filter import TokenFiltersList
from onegeo_api.views.index_profile import IndexProfilesDetail
from onegeo_api.views.index_profile import IndexProfilesIndexing
from onegeo_api.views.index_profile import IndexProfilesList
from onegeo_api.views.index_profile import IndexProfilesTasksDetail
from onegeo_api.views.index_profile import IndexProfilesTasksList
from onegeo_api.views import PdfDir
from onegeo_api.views import Protocols
from onegeo_api.views.resource import ResourcesDetail
from onegeo_api.views.resource import ResourcesList
from onegeo_api.views.search_model import Search
from onegeo_api.views.search_model import SearchModelsDetail
from onegeo_api.views.search_model import SearchModelsList
from onegeo_api.views.source import SourcesDetail
from onegeo_api.views.source import SourcesList
from onegeo_api.views.task import TasksDetail
from onegeo_api.views.task import TasksList
from onegeo_api.views.tokenizer import TokenizersDetail
from onegeo_api.views.tokenizer import TokenizersList


app_name = 'onegeo_api'


urlpatterns = [
    url('^analyzers/(?P<alias>\w+)/?$', AnalyzersDetail.as_view(), name='analyzer'),
    url('^analyzers/?$', AnalyzersList.as_view(), name='analyzers'),
    url('^catalog/?$', Catalog.as_view(), name='catalog'),
    url('^indexes/(\w+)/tasks/?$', IndexProfilesTasksList.as_view(), name='index_tasks'),
    url('^indexes/(\w+)/tasks/(\d+)/?$', IndexProfilesTasksDetail.as_view(), name='index_task'),
    url('^indexes/(?P<nickname>\w+)/?$', IndexProfilesDetail.as_view(), name='index'),
    url('^indexes/?$', IndexProfilesList.as_view(), name='indexes'),
    url('^indexes/(?P<nickname>\w+)/indexing/?$', IndexProfilesIndexing.as_view(), name='indexing'),
    url('^pdfdir/?$', PdfDir.as_view(), name='pdfdir'),
    url('^protocols/?$', Protocols.as_view(), name='protocols'),
    url('^services/(?P<nickname>\w+)/search/?$', Search.as_view(), name='search_service'),
    url('^services/(?P<nickname>\w+)/?$', SearchModelsDetail.as_view(), name='search_model'),
    url('^services/?$', SearchModelsList.as_view(), name='search_models'),
    url('^sources/(\w+)/resources/(?P<nickname>\w+)/?$', ResourcesDetail.as_view(), name='resource'),
    url('^sources/(?P<nickname>\w+)/resources/?$', ResourcesList.as_view(), name='resources'),
    url('^sources/(?P<nickname>\w+)?$', SourcesDetail.as_view(), name='source'),
    url('^sources/?$', SourcesList.as_view(), name='sources'),
    url('^tasks/(\d+)/?$', TasksDetail.as_view(), name='task'),
    url('^tasks/?$', TasksList.as_view(), name='tasks'),
    url('^tokenfilters/(?P<alias>\w+)/?$', TokenFiltersDetail.as_view(), name='tokenfilter'),
    url('^tokenfilters/?$', TokenFiltersList.as_view(), name='tokenfilters'),
    url('^tokenizers/(?P<alias>\w+)/?$', TokenizersDetail.as_view(), name='tokenizer'),
    url('^tokenizers/?$', TokenizersList.as_view(), name='tokenizers')]
