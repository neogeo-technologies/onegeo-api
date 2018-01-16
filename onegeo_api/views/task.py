from ast import literal_eval

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.http import Http404

from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Task
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import BasicAuth


@method_decorator(csrf_exempt, name="dispatch")
class TasksList(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Task.list_renderer(request.user), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class TasksDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403}, model="Task")
    def get(self, request, id):
        task = Task.get_with_permission({"id": literal_eval(id)}, request.user)
        return JsonResponse(task.detail_renderer, safe=False)
