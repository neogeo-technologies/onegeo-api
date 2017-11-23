from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.models import Resource
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth

__all__ = ["ResourceView", "ResourceIDView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_404 = {"GetResource": {"error": "Aucune resource ne correspond à cette requête."}}


@method_decorator(csrf_exempt, name="dispatch")
class ResourceView(View):

    @BasicAuth()
    def get(self, request, src_uuid):
        user = request.user

        try:
            tsk = Task.objects.get(model_type_id=src_uuid, model_type="source")
        except Task.DoesNotExist:
            data = Resource.format_by_filter(src_uuid, user=user)
            opts = {"safe": False}
        else:
            if tsk.stop_date is not None and tsk.success is True:
                data = Resource.format_by_filter(src_uuid, user=user)
                opts = {"safe": False}

            if tsk.stop_date is not None and tsk.success is False:
                data = {"error": tsk.description,
                        "task": "tasks/{}".format(tsk.id)}
                opts = {"status": 424}

            if tsk.stop_date is None and tsk.success is None:
                data = {"error": tsk.description,
                        "task": "tasks/{}".format(tsk.id)}
                opts = {"status": 423}

        return JsonResponse(data, **opts)


@method_decorator(csrf_exempt, name="dispatch")
class ResourceIDView(View):

    @BasicAuth()
    def get(self, request, src_uuid, rsrc_uuid):
        resource = Resource.get_from_uuid(rsrc_uuid, request.user)
        if not resource:
            return JsonResponse(MSG_404["GetResource"], status=404)
        return JsonResponse(resource.format_data, safe=False)
