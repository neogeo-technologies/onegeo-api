from ast import literal_eval
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import errors_on_call


@method_decorator(csrf_exempt, name="dispatch")
class TasksList(View):

    @BasicAuth()
    def get(self, request):
        defaults = {"user": request.user}
        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class TasksDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, id):
        task = Task.get_with_permission({"id": literal_eval(id)}, request.user)
        if task.success:
            return HttpResponseRedirect(task['header_location'])  # TODO: 303
        return JsonResponse(task.detail_renderer, safe=False)
