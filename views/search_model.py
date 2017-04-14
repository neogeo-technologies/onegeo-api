import json
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .. import utils
from ..elasticsearch_wrapper import elastic_conn
from ..exceptions import JsonError, MultiTaskError
from ..models import Context, SearchModel, Task



__all__ = ["SearchModelView", "SearchModelIDView", "SearchView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_406 = "Le format demandé n'est pas pris en charge. "


def search_model_context_task(ctx_id, user):
    if len(Task.objects.filter(model_type="context",
                               model_type_id=ctx_id,
                               user=user,
                               stop_date=None)) > 0:
        raise MultiTaskError()
    else:
        return True


def get_param(request, param):
    """
        Retourne la valeur d'une clé param presente dans une requete GET ou POST
    """
    if request.method == "GET":
        if param in request.GET:
            return request.GET[param]
    elif request.method == "POST":
        try:
            param_read = request.POST.get(param, request.GET.get(param))
        except KeyError as e:
            return None
        return param_read


def refresh_search_model(mdl_name, ctx_name_l):
    """Mise à jour des aliases dans ElasticSearch. """

    body = {"actions": []}

    for index in elastic_conn.get_indices_by_alias(name=mdl_name):
        body["actions"].append({"remove": {"index": index, "alias": mdl_name}})

    for context in iter(ctx_name_l):
        for index in elastic_conn.get_indices_by_alias(name=context):
            body["actions"].append({"add": {"index": index, "alias": mdl_name}})

    elastic_conn.update_aliases(body)


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelView(View):

    def get(self, request):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), SearchModel), safe=False)

    def post(self, request):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse({"Error": MSG_406}, status=406)

        data = request.body.decode("utf-8")
        body_data = json.loads(data)

        name = utils.read_name(body_data)
        if name is None:
            return JsonResponse({
                        "error":
                            "Echec de création du modèle de recherche. "
                            "Le nom du modèle de recherche est manquant. "}, status=400)

        if SearchModel.objects.filter(name=name).count() > 0:
            return JsonResponse({
                        "error":
                            "Echec de création du modèle de recherche. "
                            "Un modèle portant le même nom existe déjà. "}, status=409)

        contexts_params = "contexts" in body_data and body_data["contexts"] or []
        config = "config" in body_data and body_data["config"] or {}

        contexts = []
        for context_name in contexts_params:
            try:
                context = Context.objects.get(name=context_name)
            except Context.DoesNotExist:
                return JsonResponse({
                    "error":
                        "Echec de l'enregistrement du model de recherche. "
                        "La liste de contexte est erronée"}, status=400)
            try:
                search_model_context_task(context.pk, user())
            except MultiTaskError:
                return JsonResponse({
                    "error":
                        "Une autre tâche est en cours d'exécution. "
                        "Veuillez réessayer plus tard. "}, status=423)
            contexts.append(context)

        try:
            search_model, created = SearchModel.objects.get_or_create(
                                        user=user(), config=config, name=name)

        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=409)

        if created is False:
            return JsonResponse(data={"error": "Conflict"}, status=409)

        if created is True:
            search_model.context.set(contexts)
            search_model.save()
            if len(contexts_params) > 0:
                refresh_search_model(name, contexts_params)
            response = JsonResponse(data={}, status=201)
            response['Location'] = '{0}{1}'.format(request.build_absolute_uri(), search_model.name)
            return response


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelIDView(View):

    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        try:
            utils.user_access(name, SearchModel, user())
        except JsonError as e:
            return JsonResponse(data={"error": e.message}, status=e.status)
        return JsonResponse(utils.get_object_id(user(), name, SearchModel), status=200)

    def put(self, request, name):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse({"Error": MSG_406}, status=406)

        data = request.body.decode("utf-8")
        body_data = json.loads(data)

        name = (name.endswith('/') and name[:-1] or name)

        contexts_params = "contexts" in body_data and body_data["contexts"] or []
        config = "config" in body_data and body_data["config"] or {}

        search_model = get_object_or_404(SearchModel, name=name)
        if not search_model.user == user():
            return JsonResponse({
                        "error":
                            "Modification du modèle de recherche impossible. "
                            "Son usage est réservé."}, status=403)

        contexts = []
        for context_name in contexts_params:

            try:
                context = Context.objects.get(name=context_name)
            except Context.DoesNotExist:
                return JsonResponse({
                        "error":
                            "Echec de la modification du model de recherche. "
                            "La liste de contexte est erronée"}, status=400)

            try:
                search_model_context_task(context.pk, user())
            except MultiTaskError:
                return JsonResponse({
                        "error":
                            "Une autre tâche est en cours d'exécution. "
                            "Veuillez réessayer plus tard. "}, status=423)

            contexts.append(context)

        search_model.context.clear()
        search_model.context.set(contexts)
        search_model.config = config
        search_model.save()

        if len(contexts_params) > 0:
            refresh_search_model(name, contexts_params)

        return JsonResponse({}, status=204)

    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        name = (name.endswith('/') and name[:-1] or name)
        return utils.delete_func(name, user(), SearchModel)


@method_decorator(csrf_exempt, name='dispatch')
class SearchView(View):

    def get(self, request, name):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        search_model = get_object_or_404(SearchModel, name=name)
        if not search_model.user == user():
            return JsonResponse({
                        'error':
                            "Modification du modèle de recherche impossible. "
                            "Son usage est réservé."}, status=403)

        params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())

        if 'mode' in params and params['mode'] == 'throw':
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)
        # else:

        try:
            from importlib import import_module
            ext = import_module('...extensions.{0}'.format(name), __name__)
        except ImportError:
            from ..extensions import default as ext

        plugin = ext.plugin()
        body = plugin.input(search_model.config, **params)

        try:
            res = elastic_conn.search(index=name, body=body)
        except Exception as err:
            return JsonResponse({"error": str(err)}, status=400)
        else:
            return plugin.output(res)

    def post(self, request, name):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        search_model = get_object_or_404(SearchModel, name=name)
        if not search_model.user == user():
            return JsonResponse({
                        'error':
                            "Modification du modèle de recherche impossible. "
                            "Son usage est réservé."}, status=403)

        body = request.body.decode('utf-8')
        if not body:
            body = None

        if get_param(request, 'mode') == 'throw':
            data = elastic_conn.search(index=name, body=body)
            return JsonResponse(data=data, safe=False, status=200)
        else:
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)
