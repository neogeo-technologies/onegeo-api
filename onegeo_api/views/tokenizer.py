from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Alias
from onegeo_api.models import Tokenizer
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import errors_on_call
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class TokenizersList(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Tokenizer.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    def post(self, request):
        user = request.user

        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = read_name(body_data)
        if name is None:
            return JsonResponse({"error": "Echec de création du tokenizer. Le nom du tokenizer est manquant. "}, status=400)
        if Tokenizer.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de création du tokenizer. Un tokenizer portant le même nom existe déjà. "}, status=409)

        config = body_data.get("config", {})
        alias = body_data.get("alias", None)
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de création du tokenizer. Un tokenizer portant le même alias existe déjà. "}, status=409)
        defaults = {
            "name": name,
            "config": config,
            "alias": Alias.custom_create(model_name="Filter", handle=alias),
            "user": user
            }

        return Tokenizer.create_with_response(request, clean_my_obj(defaults))


@method_decorator(csrf_exempt, name="dispatch")
class TokenizersDetail(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions=errors_on_call())
    def get(self, request, alias):
        instance = Tokenizer.get_with_permission(slash_remove(alias), request.user)
        return JsonResponse(instance.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions=errors_on_call())
    def put(self, request, alias):

        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        token = Tokenizer.get_with_permission(slash_remove(alias), request.user)

        new_alias = body_data.get("alias", None)
        if new_alias:
            if not Alias.updating_is_allowed(new_alias, token.alias.handle):
                return JsonResponse({"error": "Echec de création du tokenizer. Un tokenizer portant le même alias existe déjà. "}, status=409)
            token.alias.update(handle=new_alias)

        config = body_data.get("config", {})
        token.update(config=config)

        return JsonResponse({}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions=errors_on_call())
    def delete(self, request, alias):
        token = Tokenizer.get_with_permission(slash_remove(alias), request.user)
        token.delete()
        return JsonResponse({}, status=204)
