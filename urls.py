from django.conf.urls import url
from .views import (SourceView, SourceIDView, ResourceView,
                    ResourceIDView, Directories, ContextView,
                    ContextIDView, FilterView, FilterIDView,
                    AnalyzerView, AnalyzerIDView, TokenizerView,
                    TokenizerIDView, ActionView, SearchModelView,
                    SearchModelIDView, SearchView, TaskView,
                    TaskIDView, SupportedModes,
                    ContextIDTaskView, ContextIDTaskIDView)


app_name = "api"
urlpatterns = [
    url(r"^sources_directories/?$", Directories.as_view()),
    url(r"^supported_modes/?$", SupportedModes.as_view()),
    url(r"^sources/(\d+)/resources/(\d+)/?$", ResourceIDView.as_view()),
    url(r"^sources/(\d+)/resources/?$", ResourceView.as_view()),
    url(r"^sources/(\d+)/?$", SourceIDView.as_view()),
    url(r"^sources/?$", SourceView.as_view()),
    url(r"^contexts/(\d+)/tasks/?$", ContextIDTaskView.as_view()),
    url(r"^contexts/(\d+)/tasks/(\d+)/?$", ContextIDTaskIDView.as_view()),
    url(r"^contexts/(\d+)/?$", ContextIDView.as_view()),
    url(r"^contexts/?$", ContextView.as_view()),
    url(r"^filters/?$", FilterView.as_view()),
    url(r"^filters/(\S+)/?$", FilterIDView.as_view()),
    url(r"^analyzers/?$", AnalyzerView.as_view()),
    url(r"^analyzers/(\S+)?$", AnalyzerIDView.as_view()),
    url(r"^tokenizers/?$", TokenizerView.as_view()),
    url(r"^tokenizers/(\S+)?$", TokenizerIDView.as_view()),
    url(r"^action/?$", ActionView.as_view()),
    url(r"^models/(\S+)/search/?$", SearchView.as_view()),
    url(r"^models/?$", SearchModelView.as_view()),
    url(r"^models/(\S+)?$", SearchModelIDView.as_view()),
    url(r"^tasks/?$", TaskView.as_view()),
    url(r"^tasks/(\d+)/?$", TaskIDView.as_view()),
]
