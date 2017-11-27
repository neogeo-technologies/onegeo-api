from ast import literal_eval
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from ..models import Task
from onegeo_api.utils import BasicAuth

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_404 = {"GetTask": {"error": "Aucune tache ne correspond à cette requête."}}


__all__ = ["TaskView", "TaskIDView"]


@method_decorator(csrf_exempt, name="dispatch")
class TaskView(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Task.format_by_filter(request.user), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class TaskIDView(View):

    @BasicAuth()
    def get(self, request, id):
        task = Task.get_from_id(literal_eval(id), request.user)
        if not task:
            return JsonResponse(MSG_404["GetTask"], status=404)
        return JsonResponse(task.format_data, safe=False)
