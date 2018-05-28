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
from onegeo_api.views.analysis import Analyses
from onegeo_api.views.catalog import Catalog
from onegeo_api.views.index_profile import IndexProfilesDetail
from onegeo_api.views.index_profile import IndexProfilesIndexing
from onegeo_api.views.index_profile import IndexProfilesList
# from onegeo_api.views.index_profile import IndexProfilesTasksDetail
# from onegeo_api.views.index_profile import IndexProfilesTasksList
from onegeo_api.views import Protocols
from onegeo_api.views.resource import ResourcesDetail
from onegeo_api.views.resource import ResourcesList
from onegeo_api.views.search_model import Search
from onegeo_api.views.search_model import SearchModelsDetail
from onegeo_api.views.search_model import SearchModelsList
from onegeo_api.views.source import SourcesDetail
from onegeo_api.views.source import SourcesList
from onegeo_api.views.task import AsyncTask
from onegeo_api.views.task import LoggedTask
from onegeo_api.views.task import LoggedTasks
from onegeo_api.views import Uris


app_name = 'onegeo_api'


urlpatterns = (
    # TODO Une seule expression regex
    url('^analysis/(?P<component>\w+)/(?P<name>\w+)/?', Analyses.as_view(), name='analysis_component'),
    url('^analysis/(?P<component>\w+)/?', Analyses.as_view(), name='analysis_components'),
    url('^analysis/?', Analyses.as_view(), name='analysis'),

    url('^catalog/?$', Catalog.as_view(), name='catalog'),

    # url('^indexes/(\w+)/tasks/(\d+)/?$', IndexProfilesTasksDetail.as_view(), name='index_task'),
    # url('^indexes/(\w+)/tasks/?$', IndexProfilesTasksList.as_view(), name='index_tasks'),

    url('^indexes/(?P<name>(\w|-){1,100})/index/?$', IndexProfilesIndexing.as_view(), name='index'),
    url('^indexes/(?P<name>(\w|-){1,100})/?$', IndexProfilesDetail.as_view(), name='index_profile'),
    url('^indexes/?$', IndexProfilesList.as_view(), name='index_profiles'),

    url('^protocols/?$', Protocols.as_view(), name='protocols'),

    url('^queue/(?P<uuid>(\w|-){1,100})/?$', AsyncTask.as_view(), name='queue'),

    url('^services/(?P<name>(\w|-){1,100})/search/?$', Search.as_view(), name='search'),
    url('^services/(?P<name>(\w|-){1,100})/?$', SearchModelsDetail.as_view(), name='search_model'),
    url('^services/?$', SearchModelsList.as_view(), name='search_models'),

    url('^sources/(?P<source>(\w|-){1,100})/resources/(?P<name>(\w|-){1,100})/?$', ResourcesDetail.as_view(), name='resource'),
    url('^sources/(?P<name>(\w|-){1,100})/resources/?$', ResourcesList.as_view(), name='resources'),
    url('^sources/(?P<name>(\w|-){1,100})/?$', SourcesDetail.as_view(), name='source'),
    url('^sources/?$', SourcesList.as_view(), name='sources'),

    url('^tasks/(?P<uuid>(\w|-){1,100})/?$', LoggedTask.as_view(), name='logged_task'),
    url('^tasks/?$', LoggedTasks.as_view(), name='logged_tasks'),

    url('^uris/?$', Uris.as_view(), name='uris'))
