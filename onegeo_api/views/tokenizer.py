import json

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from onegeo_api.exceptions import JsonError
from onegeo_api.models import Tokenizer

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404

from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.exceptions import BasicAuth
from onegeo_api.exceptions import ExceptionsHandler
from ongeo_api.models import Analyzer
from ongeo_api.models import Filter
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.utils import read_name


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_406 = "Le format demandé n'est pas pris en charge. "


@method_decorator(csrf_exempt, name="dispatch")
class TokenizerView(View):

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

        return Tokenizer.create_with_response(request, name, user, config)


@method_decorator(csrf_exempt, name="dispatch")
class TokenizerIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Tokenizer")
    def get(self, request, name):
        user = user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        instance = Tokenizer.get_with_permission(name, user)
        return JsonResponse(instance.detail_renderer)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Tokenizer")
    def put(self, request, name):

        user = request.user
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        config = body_data.get("config", {})
        name = (name.endswith('/') and name[:-1] or name)
        token = Tokenizer.get_with_permission(name, user)
        token.update(config=config)
        return JsonResponse({}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Tokenizer")
    def delete(self, request, name):
        user = request.user
        name = (name.endswith('/') and name[:-1] or name)
        return Tokenizer.delete_with_response(name, user)
