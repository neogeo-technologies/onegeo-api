from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json

from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Source
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import check_uri
from onegeo_api.utils import read_name
from onegeo_api.utils import on_http404
from onegeo_api.utils import on_http403
from onegeo_api.utils import slash_remove

__all__ = ["SourceView", "SourceIDView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_404 = {"GetSource": {"error": "Aucune source ne correspond à cette requête."}}


def is_valid_uri_for_given_mode(uri, mode):
    # TODO: Utiliser des expressions régulières mais la flemme dans l'immédiat
    if mode == "pdf" and uri[0:7] == "file://":
        return True
    if mode in ("wfs", "geonet") and uri[0:8] in ("https://", "http://"):
        return True
    return False


@method_decorator(csrf_exempt, name="dispatch")
class SourceView(View):

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
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Le nom du contexte est incorrect. "},
                                status=400)

        if not is_valid_uri_for_given_mode(body_data["uri"], body_data["mode"]):
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "L'uri est incorrecte. "},
                                status=400)
        mode = body_data["mode"]

        if mode == 'pdf':
            uri = check_uri(body_data["uri"])
            if uri is None:
                data = {"error": "Echec de création de la source. "
                                 "Le chemin d'accès à la source est incorrect. "}
                return JsonResponse(data, status=400)
        else:
            uri = body_data["uri"]

        defaults = {
            'user': user,
            'name': name,
            'mode': mode}

        return Source.create_with_response(request, uri, defaults)


@method_decorator(csrf_exempt, name="dispatch")
class SourceIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Source")
    def get(self, request, uuid):
        source = Source.get_with_permission(slash_remove(uuid), request.user)
        return JsonResponse(source.detail_renderer, safe=False)

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403}, model="Source")
    def delete(self, request, uuid):

        source = Source.get_with_permission(slash_remove(uuid), request.user)
        source.delete()
        return JsonResponse(data={}, status=204)
