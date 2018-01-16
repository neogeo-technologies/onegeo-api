from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class ResourcesList(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, src_alias):

        user = request.user
        src_alias = slash_remove(src_alias)
        source = Source.get_with_permission(src_alias, user)

        try:
            tsk = Task.objects.get(model_type_alias=source.alias.handle, model_type="source")
        except Task.DoesNotExist:
            data = Resource.list_renderer(src_alias, user)
            opts = {"safe": False}
        else:
            if tsk.stop_date and tsk.success is True:
                data = Resource.list_renderer(src_alias, user)
                opts = {"safe": False}

            if tsk.stop_date and tsk.success is False:
                data = {"error": tsk.description,
                        "task": "tasks/{}".format(tsk.id)}
                opts = {"status": 424}

            if not tsk.stop_date and not tsk.success:
                data = {"error": tsk.description,
                        "task": "tasks/{}".format(tsk.id)}
                opts = {"status": 423}
        return JsonResponse(data, **opts)


@method_decorator(csrf_exempt, name="dispatch")
class ResourcesDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, src_alias, rsrc_alias):
        resource = Resource.get_with_permission(slash_remove(rsrc_alias), request.user)
        source = Source.get_with_permission(slash_remove(src_alias), request.user)
        if resource.source != source:
            raise Http404
        return JsonResponse(resource.detail_renderer, safe=False)
