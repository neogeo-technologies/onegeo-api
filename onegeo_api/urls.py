from django.conf.urls import url

from .views.action import ActionView
from .views.context import ContextIDView
from .views.context import ContextView
from .views.context import ContextIDTaskView
from .views.context import ContextIDTaskIDView
from .views.main import Directories, SupportedModes
from .views.resource import ResourceView, ResourceIDView
from .views.search_model import SearchModelIDView, SearchModelView, SearchView
from .views.source import SourceView, SourceIDView
from onegeo_api.views.task import TaskIDView
from onegeo_api.views.task import TaskView


app_name = 'api'


urlpatterns = [
    url(r'^action/?$', ActionView.as_view()),
    url(r'^indexes/(\S+)/tasks/?$', ContextIDTaskView.as_view()),
    url(r'^indexes/(\S+)/tasks/(\d+)/?$', ContextIDTaskIDView.as_view()),
    url(r'^indexes/(\S+)/?$', ContextIDView.as_view()),
    url(r'^indexes/?$', ContextView.as_view()),
    url(r'^services/(\S+)/search/?$', SearchView.as_view()),
    url(r'^services/(\S+)/?$', SearchModelIDView.as_view()),  # URL with uuid
    url(r'^services/?$', SearchModelView.as_view()),
    url(r'^sources/(\S+)/resources/(\S+)/?$', ResourceIDView.as_view()),
    url(r'^sources/(\S+)/resources/?$', ResourceView.as_view()),
    url(r'^sources/(\S+)/?$', SourceIDView.as_view()),
    url(r'^sources/?$', SourceView.as_view()),
    url(r'^sources_directories/?$', Directories.as_view()),
    url(r'^supported_modes/?$', SupportedModes.as_view()),
    url(r'^tasks/(\d+)/?$', TaskIDView.as_view()),
    url(r'^tasks/?$', TaskView.as_view()),
]
