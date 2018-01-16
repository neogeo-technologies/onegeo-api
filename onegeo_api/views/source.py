from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json

from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Alias
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import check_uri
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove


def is_valid_uri_for_given_mode(uri, mode):
    # TODO: Utiliser des expressions régulières mais la flemme dans l'immédiat
    if mode == "pdf" and uri[0:7] == "file://":
        return True
    if mode in ("wfs", "geonet") and uri[0:8] in ("https://", "http://"):
        return True
    return False


@method_decorator(csrf_exempt, name="dispatch")
class SourcesList(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Source.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    def post(self, request):
        user = request.user

        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        field_missing = False
        if "uri" not in body_data:
            data = {"error": "Echec de création de la source. "
                             "Le chemin d'accès à la source est manquant. "}
            field_missing = True
        if "mode" not in body_data:
            data = {"error": "Echec de création de la source. "
                             "Le type de la source est manquant. "}
            field_missing = True
        if "name" not in body_data:
            data = {"error": "Echec de création de la source. "
                             "Le nom de la source est manquant. "}
            field_missing = True
        if field_missing is True:
            return JsonResponse(data, status=400)

        name = read_name(body_data)
        if name is None:
            return JsonResponse({"error": "Echec de création de la source. "
                                          "Le nom de la source est incorrect. "},
                                status=400)
        if Source.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de création de la source. "
                                          "Une source portant le même nom existe déjà. "}, status=409)

        if not is_valid_uri_for_given_mode(body_data["uri"], body_data["mode"]):
            return JsonResponse({"error": "Echec de création de la source. "
                                          "L'uri est incorrecte. "},
                                status=400)
        mode = body_data.get("mode")
        uri = body_data.get("uri")
        if mode == 'pdf':
            uri = check_uri(uri)
            if uri is None:
                data = {"error": "Echec de création de la source. "
                                 "Le chemin d'accès à la source est incorrect. "}
                return JsonResponse(data, status=400)
        if Source.objects.filter(uri=uri, user=user).exists():
            data = {"error": "Echec de création de la source. "
                             "Un usager ne peut pas définir deux sources avec le même chemin d'accés. "}
            return JsonResponse(data, status=400)

        alias = body_data.get('alias')
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de création de la source. "
                                          "Une source portant le même alias existe déjà. "}, status=409)
        defaults = {
            'user': user,
            'name': name,
            'mode': mode,
            'alias': Alias.custom_creator(model_name="Source", handle=alias),
            'uri': uri
            }
        return Source.create_with_response(request, clean_my_obj(defaults))


@method_decorator(csrf_exempt, name="dispatch")
class SourcesDetail(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Source")
    def get(self, request, alias):
        source = Source.get_with_permission(slash_remove(alias), request.user)
        return JsonResponse(source.detail_renderer, safe=False)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Source")
    def delete(self, request, alias):
        source = Source.get_with_permission(slash_remove(alias), request.user)
        for resource in Resource.objects.filter(source=source):
            resource.delete()
        Task.objects.filter(model_type_alias=source.alias.handle, model_type="source").delete()
        source.delete()
        return JsonResponse(data={}, status=204)
