import json

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.exceptions import BasicAuth
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Filter
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


@method_decorator(csrf_exempt, name="dispatch")
class TokenFilterView(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Filter.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    def post(self, request):

        user = request.user
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = read_name(body_data)
        if name is None:
            return JsonResponse({"error": "Echec de création du filtre. Le nom du filtre est manquant. "}, status=400)
        if Filter.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de création du filtre. Un filtre portant le même nom existe déjà. "}, status=409)

        config = body_data.get("config", {})
        return Filter.create_with_response(request, name, user, config)


@method_decorator(csrf_exempt, name="dispatch")
class TokenFilterIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Filter")
    def get(self, request, name):

        user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        instance = Filter.get_from_name(name, user)
        return JsonResponse(instance.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Filter")
    def put(self, request, name):

        user = request.user
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        config = body_data.get("config", {})
        name = (name.endswith('/') and name[:-1] or name)
        filter = Filter.get_with_permission(name, user)
        filter.update(config=config)
        return JsonResponse({}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Filter")
    def delete(self, request, name):
        user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        return Filter.delete_with_response(name, user)
