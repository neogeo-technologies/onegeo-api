import json
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.exceptions import BasicAuth
from onegeo_api.exceptions import ExceptionsHandler
from ongeo_api.models import Analyzer
from ongeo_api.models import Filter
from ongeo_api.models import Tokenizer
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.utils import read_name


__all__ = ["AnalyzerView", "AnalyzerIDView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerView(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Analyzer.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    @transaction.atomic
    def post(self, request):

        user = request.user

        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = read_name(body_data)
        if not name:
            return JsonResponse({"error": "Echec de création de l'analyseur. Le nom de l'analyseur est manquant."}, status=400)
        if Analyzer.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de la création de l'analyseur. Un analyseur portant le même nom existe déjà. "}, status=409)

        tokenizer = body_data.get("tokenizer", None)
        filters = body_data.get("filters", [])
        config = body_data.get("config", {})

        return Analyzer.create_with_response(
            request, name, user, config, filters, tokenizer)


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def get(self, request, name):
        user = user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        instance = Analyzer.get_with_permission(name, user)
        return JsonResponse(instance.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def put(self, request, name):
        user = request.user

        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        tokenizer = "tokenizer" in body_data and body_data["tokenizer"] or False
        filters = "filters" in body_data and body_data["filters"] or []
        config = "config" in body_data and body_data["config"] or {}

        name = (name.endswith('/') and name[:-1] or name)
        analyzer = Analyzer.get_with_permission(name, user)

        if tokenizer:
            try:
                tkn_chk = Tokenizer.objects.get(name=tokenizer)
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error": "Echec de mise à jour du tokenizer. "
                                              "Le tokenizer n'existe pas. "}, status=400)

        if analyzer.user != user:
            status = 403
            data = {"error": "Forbidden"}
        else:
            status = 204
            data = {}
            # On met à jour le champs config
            analyzer.config = config

            # On s'assure que tous les filtres existent
            for f in filters:
                if not Filter.objects.get(name=f).exists():
                    return JsonResponse({"error": "Echec de mise à jour du tokenizer. "
                                                  "La liste contient un ou plusieurs "
                                                  "filtres n'existant pas. "}, status=400)
            # Si tous corrects, on met à jour depuis un set vide
            analyzer.filter.set([])
            for f in filters:
                analyzer.filter.add(f)
            if tokenizer:
                analyzer.tokenizer = tkn_chk

            # On sauvegarde
            analyzer.save()

        return JsonResponse(data, status=status)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def delete(self, request, name):
        user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        return Analyzer.delete_with_response(name, user)
