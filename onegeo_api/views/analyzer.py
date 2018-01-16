import json
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler

from onegeo_api.utils import BasicAuth
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove

from ongeo_api.models import Alias
from ongeo_api.models import Analyzer
from ongeo_api.models import Filter
from ongeo_api.models import Tokenizer


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

        # Controle des données clients
        name = read_name(body_data)
        if not name:
            return JsonResponse({"error": "Echec de création de l'analyseur. Le nom de l'analyseur est manquant."}, status=400)
        if Analyzer.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de la création de l'analyseur. Un analyseur portant le même nom existe déjà. "}, status=409)

        alias = body_data.get("alias")
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de la création de l'analyseur. Un analyseur portant le même alias existe déjà. "}, status=409)

        tokenizer_name = body_data.get("tokenizer")
        if tokenizer_name:
            try:
                tokenizer = Tokenizer.objects.get(name=tokenizer_name)
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error": "Echec de création de l'analyseur: Le tokenizer n'existe pas. "}, status=400)

        filters_name = body_data.get("filters", [])
        filters = []
        for name in filters_name:
            try:
                currrent_filter = Filter.objects.get(name=name)
            except Filter.DoesNotExist:
                return JsonResponse({"error": "Echec de mise à jour de l'anlyseur. "
                                              "La liste contient un ou plusieurs "
                                              "filtres n'existant pas. "}, status=400)
            else:
                filters.append(currrent_filter)

        config = body_data.get("config", {})

        defaults = {
            "name": name,
            "user": user,
            "config": config,
            "tokenizer": tokenizer,
            "alias": Alias.custom_create(model_name="Analyzer", handle=alias)
            }
        return Analyzer.create_with_response(request, clean_my_obj(defaults), filters)


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def get(self, request, alias):
        user = user = request.user
        analyzer = Analyzer.get_with_permission(slash_remove(alias), user)
        return JsonResponse(analyzer.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def put(self, request, alias):
        user = request.user
        analyzer = Analyzer.get_with_permission(slash_remove(alias), user)

        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        new_alias = body_data.get("alias")
        tokenizer_name = body_data.get("tokenizer")
        filters_name = body_data.get("filters", [])
        config = body_data.get("config", {})

        # Controle des données clients
        if tokenizer_name:
            try:
                tokenizer = Tokenizer.objects.get(name=tokenizer_name)
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error": "Echec de mise à jour de l'analyseur. "
                                              "Le tokenizer n'existe pas. "}, status=400)

        filters = []
        for name in filters_name:
            try:
                currrent_filter = Filter.objects.get(name=name)
            except Filter.DoesNotExist:
                return JsonResponse({"error": "Echec de mise à jour de l'anlyseur. "
                                              "La liste contient un ou plusieurs "
                                              "filtres n'existant pas. "}, status=400)
            else:
                filters.append(currrent_filter)
            if not Filter.objects.get(name=name).exists():
                return JsonResponse({"error": "Echec de mise à jour du tokenizer. "
                                              "La liste contient un ou plusieurs "
                                              "filtres n'existant pas. "}, status=400)

        if new_alias:
            if not Alias.updating_is_allowed(new_alias, analyzer.alias.handle):
                return JsonResponse({"error": "Echec de mise à jour de l'analyseur. "
                                              "L'alias requis n'est pas disponible. "}, status=409)
            analyzer.alias.custom_updater(new_alias)

        analyzer.config = config

        if tokenizer:
            analyzer.tokenizer = tokenizer

        if len(filters) > 0:
            analyzer.filters.set(filters, clear=True)

        if tokenizer:
            analyzer.tokenizer = tokenizer

        analyzer.save()

        return JsonResponse(data={}, status=204)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Analyzer")
    def delete(self, request, alias):
        analyzer = Analyzer.get_with_permission(slash_remove(alias), request.user)
        analyzer.delete()
        return JsonResponse(data={}, status=204)
