import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils.decorators import method_decorator

from ..models import Source
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import read_name
from onegeo_api.utils import check_uri


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
        user = request.user
        return JsonResponse(Source.format_by_filter(user), safe=False)

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
        return Source.custom_create(request, uri, defaults)


@method_decorator(csrf_exempt, name="dispatch")
class SourceIDView(View):

    @BasicAuth()
    def get(self, request, uuid):
        user = request.user
        source = Source.get_from_uuid(uuid, user)
        if not source:
            return JsonResponse(MSG_404["GetSource"], status=404)
        return JsonResponse(source.format_data, safe=False)

    @BasicAuth()
    def delete(self, request, uuid):
        user = request.user
        return Source.custom_delete(uuid, user)
