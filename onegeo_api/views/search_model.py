from base64 import b64decode
from importlib import import_module
import json
from requests.exceptions import HTTPError  # TODO

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View


from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.exceptions import MultiTaskError
from onegeo_api.models import Alias
from onegeo_api.models import IndexProfile
from onegeo_api.models import SearchModel
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove
from onegeo_api.utils import retrieve_parameter
from onegeo_api.utils import errors_on_call


def search_model_index_profile_task(index_profile_alias, user):
    if Task.objects.filter(alias__handle=index_profile_alias,
                           user=user,
                           stop_date=None).exists():
        raise MultiTaskError()
    else:
        return True


def refresh_search_model(mdl_name, index_profiles_name_l):
    """
        Mise à jour des aliases dans ElasticSearch.
    """

    body = {"actions": []}

    for index in elastic_conn.get_indices_by_alias(name=mdl_name):
        body["actions"].append({"remove": {"index": index, "alias": mdl_name}})

    for index_profile in iter(index_profiles_name_l):
        for index in elastic_conn.get_indices_by_alias(name=index_profile):
            body["actions"].append({"add": {"index": index, "alias": mdl_name}})

    elastic_conn.update_aliases(body)


def read_params_SM(data):

    items = {"indexes": data.get("indexes", []),
             "config": data.get("config", {})}
    items = clean_my_obj(items)
    return items["indexes"], items["config"]


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
            error = JsonResponse(
                {"error": ("Modification du modèle de recherche impossible. "
                           "Le modèle de recherche '{}' n'existe pas. ").format(name)},
                status=404)

        if not error and sm.user != user_rq:
            sm = None
            error = JsonResponse(
                {"error": ("Modification du modèle de recherche impossible. "
                           "Son usage est réservé.")}, status=403)
    return sm, error


def get_index_profile_obj(index_profiles_clt, user):

    index_profiles_obj = []
    for index_profile_name in index_profiles_clt:
        try:
            index_profile = IndexProfile.objects.get(name=index_profile_name)
        except IndexProfile.DoesNotExist:
            raise
        try:
            search_model_index_profile_task(index_profile.alias.handle, user)
        except MultiTaskError:
            raise
        index_profiles_obj.append(index_profile)
    return index_profiles_obj


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelsList(View):

    @BasicAuth()
    def get(self, request):
        user = request.user
        return JsonResponse(SearchModel.list_renderer(user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions=errors_on_call())
    def post(self, request):
        user = request.user
        data = json.loads(request.body.decode("utf-8"))
        name = read_name(data)
        if name is None:
            return JsonResponse({"error": "Echec de création du modèle de recherche. "
                                          "Le nom est incorrect. "}, status=400)
        # if SearchModel.objects.filter(name=name).exists():
        #     return JsonResponse({"error": "Echec de création du modèle de recherche. "
        #                                   "Un modele de recherche portant le même nom existe déjà. "}, status=409)

        index_profiles = data.get("indexes", [])
        config = data.get("config", {})

        search_model, created = SearchModel.objects.get_or_create(
            name=name, defaults={"user": user, "config": config})
        if not created:
            return JsonResponse(data={"error": "Conflict"}, status=409)

        try:
            index_profiles_obj = get_index_profile_obj(index_profiles, user)
        except IndexProfile.DoesNotExist:
            return JsonResponse({
                "error":
                    "Echec de l'enregistrement du modèl de recherche. "
                    "La liste de IndexProfilee est erronée"}, status=400)
        except MultiTaskError:
            return JsonResponse({
                "error":
                    "Une autre tâche est en cours d'exécution. "
                    "Veuillez réessayer plus tard. "}, status=423)

        search_model.index_profile.set(index_profiles_obj)
        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{0}/{1}'.format(uri, search_model.alias.handle)

        if len(index_profiles) > 0:
            try:
                refresh_search_model(search_model.name, index_profiles)
            except ValueError:
                response = JsonResponse({
                    "error": "La requête a été envoyée à un serveur qui n'est pas capable de produire une réponse."
                             "(par exemple, car une connexion a été réutilisée)."}, status=421)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelsDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, alias):
        search_model = SearchModel.get_with_permision(slash_remove(alias), request.user)
        return JsonResponse(search_model.detail_renderer, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(actions=errors_on_call())
    def put(self, request, alias):
        user = request.user
        data = json.loads(request.body.decode("utf-8"))
        index_profiles = data.get("indexes", [])
        config = data.get("config", {})

        search_model = SearchModel.get_with_permission(slash_remove(alias), user)

        try:
            index_profiles_obj = get_index_profile_obj(index_profiles, user)
        except IndexProfile.DoesNotExist:
            return JsonResponse({
                "error":
                    "Echec de l'enregistrement du modèle de recherche. "
                    "La liste de IndexProfilee est erronée"}, status=400)
        except MultiTaskError:
            return JsonResponse({
                "error":
                    "Une autre tâche est en cours d'exécution. "
                    "Veuillez réessayer plus tard. "}, status=423)

        new_alias = data.get("alias", None)
        if new_alias:
            if not Alias.updating_is_allowed(new_alias, search_model.alias.handle):
                return JsonResponse({
                    "error": "Echec de la modification du modèle de recherche. "
                    "L'alias existe déjà. "}, status=409)
            search_model.alias.update_handle(new_alias)

        # RETURN RESPONSE
        search_model.index_profile.set(index_profiles_obj, clear=True)
        search_model.update(config=config)

        if len(index_profiles) > 0:
            try:
                refresh_search_model(search_model.name, index_profiles)
            except ValueError:
                return JsonResponse({
                    "error": "La requête a été envoyée à un serveur qui n'est pas capable de produire une réponse."
                             "(par exemple, une connexion a été réutilisée)."}, status=421)

        return JsonResponse({}, status=204)

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def delete(self, request, alias):
        search_model = SearchModel.get_with_permission(slash_remove(alias), request.user)
        search_model.delete()
        return JsonResponse(data={}, status=204)


# TODO(mmeliani): What We Do With Dat?
@method_decorator(csrf_exempt, name='dispatch')
class Search(View):

    @BasicAuth()
    def get(self, request, name):

        user = None
        password = None
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == 'basic':
                user, password = b64decode(auth[1]).decode("utf-8").split(":")

        search_model = get_object_or_404(SearchModel, name=name)
        params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())

        if params.get('mode', '') == 'throw':
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)

        return JsonResponse(data={'error': 'Not implemented.'}, status=501)

        try:
            ext = import_module('...extensions.{0}'.format(name), __name__)
        except ImportError:
            ext = import_module('...extensions.__init__', __name__)

        index_profiles = [
            e.index_profile
            for e in SearchModel.index_profile.through.objects.filter(
                earchmodel=search_model)]

        try:
            plugin = ext.plugin(
                search_model.config, index_profiles, user=user, password=password)
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

    # @ContentTypeLookUp()
    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def post(self, request, alias):

        user = request.user

        search_model = SearchModel.get_with_permission(slash_remove(alias), user)

        body = request.body.decode('utf-8')
        if not body:
            body = None

        if retrieve_parameter(request, 'mode') == 'throw':
            data = elastic_conn.search(index=search_model.name, body=body)
            return JsonResponse(data=data, safe=False, status=200)
        else:
            return JsonResponse(data={'error': 'Not implemented.'}, status=501)
