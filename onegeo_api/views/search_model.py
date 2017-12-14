from base64 import b64decode
from importlib import import_module
import json
from requests.exceptions import HTTPError  # TODO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.http import Http404

from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.exceptions import MultiTaskError
from onegeo_api.models import Context
from onegeo_api.models import SearchModel
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove


__all__ = ["SearchModelView", "SearchModelIDView", "SearchView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


def search_model_context_task(ctx_uuid, user):
    if len(Task.objects.filter(model_type="context",
                               model_type_id=ctx_uuid,
                               user=user,
                               stop_date=None)) > 0:
        raise MultiTaskError()
    else:
        return True


def get_param(request, param):
    """
        Retourne la valeur d'une clé param presente dans une requete GET ou POST.
    """
    if request.method == "GET":
        if param in request.GET:
            return request.GET[param]
    elif request.method == "POST":
        try:
            param_read = request.POST.get(param, request.GET.get(param))
        except KeyError:
            return None
        return param_read


def refresh_search_model(mdl_name, ctx_name_l):
    """
        Mise à jour des aliases dans ElasticSearch.
    """

    body = {"actions": []}

    for index in elastic_conn.get_indices_by_alias(name=mdl_name):
        body["actions"].append({"remove": {"index": index, "alias": mdl_name}})

    for context in iter(ctx_name_l):
        for index in elastic_conn.get_indices_by_alias(name=context):
            body["actions"].append({"add": {"index": index, "alias": mdl_name}})

    elastic_conn.update_aliases(body)


def read_params_SM(data):

    items = {"indexes": data.get("indexes", []),
             "config": data.get("config", {})}
    items = clean_my_obj(items)
    return items["indices"], items["config"]


def get_search_model(name, user_rq, config, method):

    sm = None
    error = None

    if method == 'POST':
        try:
            sm, created = SearchModel.objects.get_or_create(
                name=name, defaults={"user": user_rq, "config": config})

        except ValidationError as e:
            error = JsonResponse({"error": e.message}, status=409)
        if created is False:
            error = JsonResponse(data={"error": "Conflict"}, status=409)

    elif method == 'PUT':
        try:
            sm = SearchModel.objects.get(name=name)
        except SearchModel.DoesNotExist:
            sm = None
            error = JsonResponse({
                        "error":
                            "Modification du modèle de recherche impossible. "
                            "Le modèle de recherche '{}' n'existe pas. ".format(name)
                        }, status=404)

        if not error and sm.user != user_rq:
            sm = None
            error = JsonResponse({
                        "error":
                            "Modification du modèle de recherche impossible. "
                            "Son usage est réservé."}, status=403)
    return sm, error


def get_contexts_obj(contexts_clt, user):

    contexts_obj = []
    for context_name in contexts_clt:
        try:
            context = Context.objects.get(name=context_name)
        except Context.DoesNotExist:
            raise
        try:
            search_model_context_task(context.uuid, user)
        except MultiTaskError:
            raise
        contexts_obj.append(context)
    return contexts_obj


def set_search_model_contexts(search_model, contexts_obj,
                              contexts_clt, request, config=None):

    response = None

    if request.method == "POST":
        search_model.context.set(contexts_obj)
        search_model.save()
        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{0}/{1}'.format(uri, search_model.name)

        if len(contexts_clt) > 0:
            try:
                refresh_search_model(search_model.name, contexts_clt)
            except ValueError:
                response = JsonResponse({
                    "error": "La requête a été envoyée à un serveur qui n'est pas capable de produire une réponse."
                             "(par exemple, car une connexion a été réutilisée)."}, status=421)

    if request.method == "PUT":
        search_model.context.clear()
        search_model.context.set(contexts_obj)
        search_model.config = config
        search_model.save()
        response = JsonResponse({}, status=204)

        if len(contexts_clt) > 0:
            try:
                refresh_search_model(search_model.name, contexts_clt)
            except ValueError:
                response = JsonResponse({
                    "error": "La requête a été envoyée à un serveur qui n'est pas capable de produire une réponse."
                             "(par exemple, car une connexion a été réutilisée)."}, status=421)

    return response


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelView(View):

    @BasicAuth()
    def get(self, request):
        user = request.user
        return JsonResponse(SearchModel.custom_filter(user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    def post(self, request):

        user = request.user
        data = json.loads(request.body.decode("utf-8"))
        name = read_name(data)
        contexts_clt, config_clt = read_params_SM(data)

        search_model, error = \
            get_search_model(name, user, config_clt, request.method)
        if error:
            return error

        try:
            contexts_obj = get_contexts_obj(contexts_clt, user)
        except Context.DoesNotExist:
            return JsonResponse({
                "error":
                    "Echec de l'enregistrement du model de recherche. "
                    "La liste de contexte est erronée"}, status=400)
        except MultiTaskError:
            return JsonResponse({
                "error":
                    "Une autre tâche est en cours d'exécution. "
                    "Veuillez réessayer plus tard. "}, status=423)

        return set_search_model_contexts(search_model,
                                         contexts_obj,
                                         contexts_clt,
                                         request,
                                         config=None)


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="SearchModel")
    def get(self, request, name):
        user = request.user
        sm = SearchModel.user_access(slash_remove(name), user)
        return JsonResponse(sm.format_data, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="SearchModel")
    def put(self, request, name):
        # READ REQUEST DATA
        user = request.user
        data = json.loads(request.body.decode("utf-8"))
        name = slash_remove(name)
        contexts_clt, config_clt = read_params_SM(data)

        # GET SearchModel
        search_model, error = \
            get_search_model(name, user(), config_clt, request.method)
        if error:
            return error

        try:
            contexts_obj = get_contexts_obj(contexts_clt, user())
        except Context.DoesNotExist:
            return JsonResponse({
                "error":
                    "Echec de l'enregistrement du model de recherche. "
                    "La liste de contexte est erronée"}, status=400)
        except MultiTaskError:
            return JsonResponse({
                "error":
                    "Une autre tâche est en cours d'exécution. "
                    "Veuillez réessayer plus tard. "}, status=423)

        # RETURN RESPONSE
        return set_search_model_contexts(search_model,
                                         contexts_obj,
                                         contexts_clt,
                                         request,
                                         config_clt)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="SearchModel")
    def delete(self, request, name):
        user = request.user
        sm = SearchModel.user_access(slash_remove(name), user)
        sm.delete()
        return JsonResponse(data={}, status=204)


# TODO(mmeliani): Revoir gestion des plugins
@method_decorator(csrf_exempt, name='dispatch')
class SearchView(View):

    def get(self, request, name):

        user = None
        password = None
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == 'basic':
                user, password = b64decode(auth[1]).decode("utf-8").split(":")

        search_model = get_object_or_404(SearchModel, name=name)
        params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())

        if 'mode' in params and params['mode'] == 'throw':
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)
        # else:

        try:
            ext = import_module('...extensions.{0}'.format(name), __name__)
        except ImportError:
            ext = import_module('...extensions.__init__', __name__)

        contexts = [e.context
                    for e in SearchModel.context.through.objects.filter(
                        searchmodel=search_model)]

        try:
            plugin = ext.plugin(
                search_model.config, contexts, user=user, password=password)
        except HTTPError as err:
            return JsonResponse({"error": str(err)}, status=err.response.status_code)
        except Exception as err:
            return JsonResponse({"error": str(err)}, status=400)

        body = plugin.input(**params)
        try:
            res = elastic_conn.search(index=name, body=body)
        except Exception as err:
            return JsonResponse({"error": str(err)}, status=400)
        else:
            return plugin.output(res)

    @BasicAuth()
    def post(self, request, name):

        user = request.user

        search_model = get_object_or_404(SearchModel, name=name)
        if not search_model.user == user:
            return JsonResponse({
                'error': "Modification du modèle de recherche impossible. "
                         "Son usage est réservé."}, status=403)

        body = request.body.decode('utf-8')
        if not body:
            body = None

        if get_param(request, 'mode') == 'throw':
            data = elastic_conn.search(index=name, body=body)
            return JsonResponse(data=data, safe=False, status=200)
        else:
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)
