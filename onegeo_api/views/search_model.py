# from base64 import b64decode
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
# from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from elasticsearch import Elasticsearch
# from importlib import import_module
import json
# from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
# from onegeo_api.exceptions import MultiTaskError
# from onegeo_api.models import Alias
from onegeo_api.models import IndexProfile
from onegeo_api.models import SearchModel
# from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
# from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import errors_on_call
# from onegeo_api.utils import read_name
# from onegeo_api.utils import retrieve_parameter
# from onegeo_api.utils import slash_remove
import re
import requests
# from requests.exceptions import HTTPError  # TODO


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelsList(View):

    @BasicAuth()
    def get(self, request):
        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True}
        return JsonResponse(
            SearchModel.list_renderer(request.user, **opts), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    # @ExceptionsHandler(actions=errors_on_call())
    def post(self, request):
        # creation du profil de recherche
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': str(e)}, status=400)
        data['user'] = request.user
        indexes = data.pop('indexes')

        if 'name' not in data:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse({'error': msg}, status=400)

        try:
            instance = SearchModel.objects.create(**data)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except IntegrityError as e:
            return JsonResponse({'error': str(e)}, status=409)

        for item in indexes:
            try:
                index_nickname = re.search('^/indexes/(\w+)/?$', item).group(1)
            except AttributeError as e:
                return JsonResponse({'error': str(e)}, status=400)
            instance.index_profiles.add(IndexProfile.get_or_raise(index_nickname,
                                        data['user']))

        response = HttpResponse(status=201)
        response['Content-Location'] = instance.location
        return response


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelsDetail(View):

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):
        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True}
        search_model = SearchModel.get_or_raise(nickname, request.user)

        return JsonResponse(
            search_model.detail_renderer(**opts),
            status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    # @ExceptionsHandler(actions=errors_on_call())
    def put(self, request, nickname):
        # mise à jour du profile de recherche
        try:
            data = json.loads(request.body.decode('utf-8'))
            data.pop('indexes_list')
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        user = request.user
        search_model = SearchModel.get_or_raise(nickname, user)

        # TODO: JSON must be complete. Check this.
        if 'name' not in data \
                or 'indexes' not in data \
                or 'config' not in data:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse({'error': msg}, status=400)

        # mise à jour du paramètres config
        if 'config' in data:
            try:
                search_model.config = json.loads(data['config'])
            except:
                # return JsonResponse("requete n'est pas au bon format")
                # to do aavec message erreur
                pass

        # mise à jour des indexes
        index_profiles = []
        for item in data.pop('indexes'):
            try:
                index_nickname = re.search('^/indexes/(\w+)/?$', item).group(1)
            except AttributeError as e:
                return JsonResponse({'error': str(e)}, status=400)
            index_profiles.append(
                IndexProfile.get_or_raise(index_nickname, user))
        search_model.index_profiles.set(index_profiles, clear=True)

        for k, v in data.items():
            if k == "location":
                setattr(search_model, k+"__name", v)

        try:
            search_model.save()
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except IntegrityError as e:
            return JsonResponse({'error': str(e)}, status=409)

        return HttpResponse(status=204)

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def delete(self, request, nickname):
        search_model = SearchModel.get_or_raise(nickname, request.user)
        search_model.delete()
        return JsonResponse(data={}, status=204)


@method_decorator(csrf_exempt, name='dispatch')
class Search(View):

    # @BasicAuth()
    def get(self, request, nickname):

        # QUERY PARAMETERS
        parameters = ""
        # TO DOOOO
        user = User.objects.get(username="salima")
        # recuperation du profile recherche
        try:
            search_model = SearchModel.get_or_raise(nickname, user)
            try:
                config = json.loads(json.dumps(search_model.config))
            except ValueError:
                config = search_model.config
        except ValidationError as e:
            JsonResponse({"error": e.message})

        index_profiles = search_model.index_profiles.all()
        index_profiles_alias = list(index_profiles.values_list('alias__handle',
                                    flat=True))
        # garde seulement les index dispo dans elastic search
        query_url = settings.ELASTIC_URL+"_aliases"
        resource_alias = requests.get(query_url.encode('utf8')).json()
        es_alias = [list(elt['aliases'].keys())[0] if elt['aliases'].keys() else "" for elt in resource_alias.values()]
        # intersection des 2 listes
        index_profiles_alias = set(index_profiles_alias).intersection(es_alias)
        index_profiles_alias = ','.join(index_profiles_alias)

        # Construction de la requete et envoie à Elastic Search
        # ajouter les parametres transmis dans la requete
        try:
            if parameters:
                req = requests.get(settings.ELASTIC_URL + index_profiles_alias
                                   + "/_search?" + parameters)
            elif config:
                es = Elasticsearch(settings.ELASTIC_URL, use_ssl=False,
                                   verify_certs=False)
                req = es.search(index=index_profiles_alias,
                                # doc_type = 'doc',
                                body=config or {'query': {'match_all': {}}})
                return JsonResponse(req, safe=False)

            else:
                req = requests.get(settings.ELASTIC_URL + index_profiles_alias
                                   + "/_search?")
            return JsonResponse(req.json(), safe=False)
        except requests.exceptions.HTTPError as err:
            return JsonResponse("Elastic Search non accesible", safe=False)



# def search_model_index_profile_task(index_profile_alias, user):
#     if Task.objects.filter(alias__handle=index_profile_alias,
#                            user=user,
#                            stop_date=None).exists():
#         raise MultiTaskError()
#     else:
#         return True

#
# def refresh_search_model(mdl_name, index_profiles_name_l):
#     pass
#     """
#         Mise à jour des aliases dans ElasticSearch.
#     """
#
#     body = {"actions": []}
#
#     for index in elastic_conn.get_indices_by_alias(name=mdl_name):
#         body["actions"].append({"remove": {"index": index, "alias": mdl_name}})
#
#     for index_profile in iter(index_profiles_name_l):
#         for index in elastic_conn.get_indices_by_alias(name=index_profile):
#             body["actions"].append({"add": {"index": index, "alias": mdl_name}})
#
#     elastic_conn.update_aliases(body)
#
#
# def read_params_SM(data):
#
#     items = {"indexes": data.get("indexes", []),
#              "config": data.get("config", {})}
#     items = clean_my_obj(items)
#     return items["indexes"], items["config"]
#
#
# def get_search_model(name, user_rq, config, method):
#
#     sm = None
#     error = None
#
#     if method == 'POST':
#         try:
#             sm, created = SearchModel.objects.get_or_create(
#                 name=name, defaults={"user": user_rq, "config": config})
#
#         except ValidationError as e:
#             error = JsonResponse({"error": e.message}, status=409)
#         if created is False:
#             error = JsonResponse(data={"error": "Conflict"}, status=409)
#
#     elif method == 'PUT':
#         try:
#             sm = SearchModel.objects.get(name=name)
#         except SearchModel.DoesNotExist:
#             sm = None
#             error = JsonResponse(
#                 {"error": ("Modification du modèle de recherche impossible. "
#                            "Le modèle de recherche '{}' n'existe pas. ").format(name)},
#                 status=404)
#
#         if not error and sm.user != user_rq:
#             sm = None
#             error = JsonResponse(
#                 {"error": ("Modification du modèle de recherche impossible. "
#                            "Son usage est réservé.")}, status=403)
#     return sm, error


# def get_index_profile_obj(index_profiles_clt, user):
#     index_profiles_obj = []
#     for index_profile_name in index_profiles_clt:
#         data = search('^/indexes/(\S+)/?$', index_profile_name)
#         index_profile = IndexProfile.objects.get(alias__handle=data.group(1))
#         search_model_index_profile_task(index_profile.alias.handle, user)
#         index_profiles_obj.append(index_profile)
#     return index_profiles_obj


# # TODO(mmeliani): What We Do With Dat?
# @method_decorator(csrf_exempt, name='dispatch')
# class Search(View):
#
#     @BasicAuth()
#     def get(self, request, name):
#
#         user = None
#         password = None
#         if 'HTTP_AUTHORIZATION' in request.META:
#             auth = request.META['HTTP_AUTHORIZATION'].split()
#             if len(auth) == 2 and auth[0].lower() == 'basic':
#                 user, password = b64decode(auth[1]).decode("utf-8").split(":")
#
#         search_model = get_object_or_404(SearchModel, name=name)
#         params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())
#
#         if params.get('mode', '') == 'throw':
#             return JsonResponse(data={'error': 'Not implemented.'}, status=501)
#
#         return JsonResponse(data={'error': 'Not implemented.'}, status=501)
#
#         try:
#             ext = import_module('...extensions.{0}'.format(name), __name__)
#         except ImportError:
#             ext = import_module('...extensions.__init__', __name__)
#
#         index_profiles = [
#             e.index_profile
#             for e in SearchModel.index_profile.through.objects.filter(
#                 earchmodel=search_model)]
#
#         try:
#             plugin = ext.plugin(
#                 search_model.config, index_profiles, user=user, password=password)
#         except HTTPError as err:
#             return JsonResponse({"error": str(err)}, status=err.response.status_code)
#         except Exception as err:
#             return JsonResponse({"error": str(err)}, status=400)
#
#         body = plugin.input(**params)
#         try:
#             res = elastic_conn.search(index=name, body=body)
#         except Exception as err:
#             return JsonResponse({"error": str(err)}, status=400)
#         else:
#             return plugin.output(res)
#
#     # @ContentTypeLookUp()
#     @BasicAuth()
#     @ExceptionsHandler(actions=errors_on_call())
#     def post(self, request, alias):
#
#         user = request.user
#         # a modifier foncionne non implementer  TODOOOOOO
#         search_model = SearchModel.get_with_permission(slash_remove(alias), user)
#
#         body = request.body.decode('utf-8')
#         if not body:
#             body = None
#
#         if retrieve_parameter(request, 'mode') == 'throw':
#             data = elastic_conn.search(index=search_model.name, body=body)
#             return JsonResponse(data=data, safe=False, status=200)
#         else:
#             return JsonResponse(data={'error': 'Not implemented.'}, status=501)
