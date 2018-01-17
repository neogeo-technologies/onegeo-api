import json

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Alias
from onegeo_api.models import Filter
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class TokenFiltersList(View):

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
        alias = body_data.get("alias")
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Un contexte portant le même alias existe déjà. "}, status=409)
        defaults = {
            "name": name,
            "config": config,
            "alias": Alias.custom_create(model_name="Filter", handle=alias),
            "user": user
            }

        return Filter.create_with_response(request, clean_my_obj(defaults))


@method_decorator(csrf_exempt, name="dispatch")
class TokenFiltersDetail(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, alias):
        instance = Filter.get_with_permission(slash_remove(alias), request.user)
        return JsonResponse(instance.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def put(self, request, alias):
        instance = Filter.get_with_permission(slash_remove(alias), request.user)

        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        config = body_data.get("config", {})
        new_alias = body_data.get("alias", None)

        if new_alias:
            if not Alias.updating_is_allowed(new_alias, instance.alias.handle):
                return JsonResponse({"error": "Echec de la création du contexte d'indexation. L'alias existe déjà. "}, status=409)
            instance.alias.custom_updater(new_alias)

        instance.update(config=config)

        return JsonResponse({}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def delete(self, request, alias):
        user = request.user
        instance = Filter.get_with_permission(slash_remove(alias), user)
        instance.delete()
        return JsonResponse(data={}, status=204)
