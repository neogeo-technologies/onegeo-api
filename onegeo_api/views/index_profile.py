from ast import literal_eval
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from re import search
import json

from onegeo_manager.context import Context as OnegeoContext
from onegeo_manager.index import Index as OnegeoIndex
from onegeo_manager.resource import Resource as OnegeoResource
from onegeo_manager.source import Source as OnegeoSource

from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Alias
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove
from onegeo_api.utils import errors_on_call


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesList(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(IndexProfile.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions=errors_on_call())
    def post(self, request):
        import pdb; pdb.set_trace()
        user = request.user
        body_data = json.loads(request.body.decode('utf-8'))
        if not body_data.get('name'):
            return JsonResponse({"error": "Echec la création du profil d'indexation. "
                                          "Le nom du IndexProfilee est manquant. "}, status=400)
        if not body_data.get('resource'):
            return JsonResponse({"error": "Echec de création du profil d'indexation. "
                                          "Le chemin d'accès est manquant. "}, status=400)

        name = read_name(body_data)
        if name is None:
            return JsonResponse({"error": "Echec de création du profil d'indexation. "
                                          "Le nom du IndexProfile est incorrect. "}, status=400)
        if IndexProfile.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de création du profil d'indexation. "
                                          "Un IndexProfilee portant le même nom existe déjà. "}, status=409)

        reindex_frequency = body_data.get("reindex_frequency", "monthly")

        data = search('^/sources/(\S+)/resources/(\S+)$', body_data.get('resource'))
        if not data:
            return JsonResponse({"error": "Echec de création du profil d'indexation. "
                                          "Les identifiants des source et ressource sont erronées. "}, status=400)
        src_alias = data.group(1)
        rsrc_alias = data.group(2)

        resource = Resource.get_with_permission(rsrc_alias, request.user)
        source = Source.get_with_permission(src_alias, request.user)

        if source != resource.source:
            return JsonResponse({"error": "Echec de création du profil d'indexation. "
                                          "Les identifiants des source et ressource sont erronées. "}, status=400)

        onegeo_source = OnegeoSource(source.uri, name, source.protocol)
        onegeo_resource = OnegeoResource(onegeo_source, resource.name)
        for col in iter(resource.columns):
            if onegeo_resource.is_existing_column(col["name"]):
                continue
            onegeo_resource.add_column(
                col["name"], column_type=col["type"],
                occurs=tuple(col["occurs"]), count=col["count"],
                rule="rule" in col and col["rule"] or None)

        onegeo_index = OnegeoIndex(resource.name)
        onegeo_IndexProfile = OnegeoContext(name, onegeo_index, onegeo_resource)
        clmn_properties = []
        for ppt in onegeo_IndexProfile.iter_properties():
            clmn_properties.append(ppt.all())

        alias = body_data.get('alias')
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de création du IndexProfilee d'indexation. "
                                          "Un IndexProfilee portant le même alias existe déjà. "}, status=409)
        defaults = {
            'user': user,
            'name': name,
            'alias': Alias.custom_create(model_name="IndexProfile", handle=alias),
            'clmn_properties': clmn_properties,
            'reindex_frequency': reindex_frequency,
            }
        return IndexProfile.create_with_response(
            request, defaults, resource)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesDetail(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions=errors_on_call())
    def get(self, request, alias):
        index_profile = IndexProfile.get_with_permission(slash_remove(alias), request.user)
        return JsonResponse(index_profile.detail_renderer, safe=False, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions=errors_on_call())
    def put(self, request, alias):
        index_profile = IndexProfile.get_with_permission(slash_remove(alias), request.user)

        body_data = json.loads(request.body.decode('utf-8'))
        name = body_data.get('name')
        reindex_frequency = body_data.get('reindex_frequency')
        list_ppt_clt = body_data.get('columns', {})

        data = search('^/sources/(\S+)/resources/(\S+)$', body_data.get('resource'))
        if not data:
            return JsonResponse({"error": "Echec de la modification du profil d'indexation. "
                                          "Les identifiants des source et ressource sont erronées. "}, status=400)
        src_alias = data.group(1)
        rsrc_alias = data.group(2)

        resource = Resource.get_with_permission(rsrc_alias, request.user)
        source = Source.get_with_permission(src_alias, request.user)

        if source != resource.source:
            return JsonResponse({"error": "Echec de la modification du profil d'indexation. "
                                          "Les identifiants des source et ressource sont erronées. "}, status=400)
        resource.index_profile = index_profile
        try:
            resource.save()
        except Exception as e:
            return JsonResponse(data={"error": e.message}, status=409)

        new_alias = body_data.get("alias")
        if new_alias:
            if not Alias.updating_is_allowed(new_alias, index_profile.alias.handle):
                return JsonResponse({"error": "Echec de la création de l'analyseur. Un analyseur portant le même alias existe déjà. "}, status=409)
            index_profile.alias.update_handle(new_alias)

        index_profile.update_clmn_properties(list_ppt_clt)

        if name:
            index_profile.name = name
        if reindex_frequency:
            index_profile.reindex_frequency = reindex_frequency

        index_profile.save()

        return JsonResponse(data={}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions=errors_on_call())
    def delete(self, request, alias):
        index_profile = IndexProfile.get_with_permission(slash_remove(alias), request.user)
        # Erreur sur IndexProfile.delete() suite a erreur sur elasticsearch_wrapper
        # "elastic_conn.delete_index_by_alias" doit etre réintégrer
        index_profile.delete()
        return JsonResponse(data={}, status=204)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksList(View):

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, alias):
        import pdb; pdb.set_trace()
        index_profile = IndexProfile.get_with_permission(slash_remove(alias), request.user)
        defaults = {
            "alias": index_profile.alias,
            "user": request.user
            }

        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, alias, tsk_id):
        index_profile = IndexProfile.get_with_permission(slash_remove(alias), request.user)
        defaults = {
            "id": literal_eval(tsk_id),
            "alias": index_profile.alias,
            }
        task = Task.get_with_permission(defaults, request.user)
        return JsonResponse(task.detail_renderer, safe=False)
