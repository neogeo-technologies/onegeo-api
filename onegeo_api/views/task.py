from ast import literal_eval
from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Task
from onegeo_api import utils


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


@method_decorator(csrf_exempt, name="dispatch")
class TaskView(View):

    def get(self, request):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Task), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class TaskIDView(View):

    def get(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        tsk_id = literal_eval(id)
        return JsonResponse(utils.get_object_id(user(), tsk_id, Task), safe=False)
