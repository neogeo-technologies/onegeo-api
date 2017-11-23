import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils.decorators import method_decorator
from pathlib import Path

from ..models import Source
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import format_json_get_create
from onegeo_api.utils import read_name


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


def check_uri(b):
    """
    Verifie si l'uri en param d'entrée recu sous la forme de "file:///dossier"
    Correspond a un des dossiers enfant du dossier parent PDF_BASE_DIR
    Retourne l'uri complete si correspondance, None sinon.
    NB: l'uri complete sera verifier avant tout action save() sur modele Source()
    """
    p = Path(PDF_BASE_DIR)
    if not p.exists():
        raise ConnectionError("Given path does not exist.")
    for x in p.iterdir():
        if x.is_dir() and x.name == b[8:]:
            return x.as_uri()
    return None


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
            np = check_uri(body_data["uri"])
            if np is None:
                data = {"error": "Echec de création de la source. "
                                 "Le chemin d'accès à la source est incorrect. "}
                return JsonResponse(data, status=400)
        else:
            np = body_data["uri"]

        sources, created = Source.objects.get_or_create(uri=np, defaults={'user': user,
                                                                          'name': name,
                                                                          'mode': mode})

        status = created and 201 or 409
        return format_json_get_create(request, created, status, str(sources.short_uuid))


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
