from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
# from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
# from onegeo_api.utils import errors_on_call
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class ResourcesList(View):

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):
        user = request.user
        nickname = slash_remove(nickname)
        source = Source.get_or_raise(nickname, user)

        try:
            tsk = Task.objects.get(alias=source.alias)
        except Task.DoesNotExist:
            data = Resource.list_renderer(nickname, user)
            opts = {"safe": False}
        else:
            if tsk.stop_date and tsk.success is True:
                data = Resource.list_renderer(nickname, user)
                opts = {"safe": False}

            if tsk.stop_date and tsk.success is False:
                data = {"error": tsk.description,
                        "task": "/tasks/{}".format(tsk.id)}
                opts = {"status": 424}

            if not tsk.stop_date and not tsk.success:
                data = {"error": tsk.description,
                        "task": "/tasks/{}".format(tsk.id)}
                opts = {"status": 423}

        return JsonResponse(data, **opts)


@method_decorator(csrf_exempt, name="dispatch")
class ResourcesDetail(View):

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):
        resource = Resource.get_or_raise(slash_remove(nickname), request.user)
        return JsonResponse(resource.detail_renderer())
