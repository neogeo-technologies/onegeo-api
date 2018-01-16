from ast import literal_eval
from django.core.exceptions import PermissionDenied
from django.http import Http404
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
from onegeo_api.models import Context
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class ContextsList(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Context.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def post(self, request):
        user = request.user
        body_data = json.loads(request.body.decode('utf-8'))
        if not body_data.get('name'):
            return JsonResponse({"error": "Echec la création du contexte d'indexation. "
                                          "Le nom du contexte est manquant. "}, status=400)
        if not body_data.get('resource'):
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Le chemin d'accès est manquant. "}, status=400)

        name = read_name(body_data)
        if name is None:
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Le nom du context est incorrect. "}, status=400)
        if Context.objects.filter(name=name).exists():
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Un contexte portant le même nom existe déjà. "}, status=409)

        reindex_frequency = body_data.get("reindex_frequency", "monthly")

        # data = search('^/sources/(\S+)/resources/(\S+)$', body_data['resource'])
        # if not data:
        #     raise Http404
        # src_uuid = data.group(1)
        # rsrc_uuid = data.group(2)
        # resource = Resource.get_with_permission(rsrc_uuid, request.user)
        # source = Source.get_with_permission(src_uuid, request.user)
        #
        # if source != resource.source:
        #     return JsonResponse({"error": "Echec de création du contexte d'indexation. "
        #                                   "Les identifiants des source et ressource sont erronées. "}, status=400)
        resources_to_relate = []
        for uri in body_data['resource']:
            data = search('^/sources/(\S+)/resources/(\S+)$', uri)
            if not data:
                return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                              "Les identifiants des source et ressource sont erronées. "}, status=400)
            src_alias = data.group(1)
            rsrc_alias = data.group(2)

            resource = Resource.get_with_permission(rsrc_alias, request.user)
            try:
                source = Source.get_with_permission(src_alias, request.user)
            except:
                raise

            if source != resource.source:
                return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                              "Les identifiants des source et ressource sont erronées. "}, status=400)
            resources_to_relate.append(resource)

            onegeo_source = OnegeoSource(source.uri, name, source.mode)
            onegeo_resource = OnegeoResource(onegeo_source, resource.name)
            for col in iter(resource.columns):
                if onegeo_resource.is_existing_column(col["name"]):
                    continue
                onegeo_resource.add_column(
                    col["name"], column_type=col["type"],
                    occurs=tuple(col["occurs"]), count=col["count"],
                    rule="rule" in col and col["rule"] or None)

            onegeo_index = OnegeoIndex(resource.name)
            onegeo_context = OnegeoContext(name, onegeo_index, onegeo_resource)
            clmn_properties = []
            for ppt in onegeo_context.iter_properties():
                clmn_properties.append(ppt.all())

        alias = body_data.get('alias')
        if alias and Alias.objects.filter(handle=alias).exists():
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Un contexte portant le même alias existe déjà. "}, status=409)
        defaults = {
            'user': user,
            'name': name,
            'alias': Alias.custom_creator(model_name="Context", handle=alias),
            'clmn_properties': clmn_properties,
            'reindex_frequency': reindex_frequency,
            }
        return Context.create_with_response(
            request, defaults, resources_to_relate)


@method_decorator(csrf_exempt, name="dispatch")
class ContextsDetail(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, alias):
        context = Context.get_with_permission(slash_remove(alias), request.user)
        return JsonResponse(context.detail_renderer, safe=False, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def put(self, request, alias):
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = body_data.get('name')
        reindex_frequency = body_data.get('reindex_frequency')
        list_ppt_clt = body_data.get('columns', {})

        resources_to_relate = []
        for uri in body_data['resource']:
            data = search('^/sources/(\S+)/resources/(\S+)$', uri)
            if not data:
                return JsonResponse({"error": "Echec de la modification du contexte d'indexation. "
                                              "Les identifiants des source et ressource sont erronées. "}, status=400)
            src_alias = data.group(1)
            rsrc_alias = data.group(2)

            resource = Resource.get_with_permission(rsrc_alias, request.user)
            source = Source.get_with_permission(src_alias, request.user)

            if source != resource.source:
                return JsonResponse({"error": "Echec de la modification du contexte d'indexation. "
                                              "Les identifiants des source et ressource sont erronées. "}, status=400)
            resources_to_relate.append(resource)

        context = Context.get_with_permission(slash_remove(alias), request.user)

        new_alias = body_data.get("alias")
        if new_alias:
            if not Alias.updating_is_allowed(new_alias, context.alias.handle):
                return JsonResponse({"error": "Echec de la création de l'analyseur. Un analyseur portant le même alias existe déjà. "}, status=409)
            context.alias.custom_updater(new_alias)

        context.update_clmn_properties(list_ppt_clt)

        for resource in resources_to_relate:
            resource.context = context
            try:
                resource.save()
            except Exception as e:
                return JsonResponse(data={"error": e.message}, status=409)

        if name:
            context.name = name
        if reindex_frequency:
            context.reindex_frequency = reindex_frequency

        context.save()

        return JsonResponse(data={}, status=204)

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def delete(self, request, alias):
        context = Context.get_with_permission(slash_remove(alias), request.user)
        context.delete()  # Erreur sur signal delete_context suite a erreur sur elasticsearch_wrapper
        # CF signals.py "elastic_conn.delete_index_by_alias" a réintégrer
        return JsonResponse(data={"error": "Context supprimé, elastic_conn.delete_index_by_alias non appliqué"}, status=204)


@method_decorator(csrf_exempt, name="dispatch")
class ContextsTasksList(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, alias):

        context = Context.get_with_permission(slash_remove(alias), request.user)
        defaults = {
            "model_type": "context",
            "model_type_alias": context.alias.handle,
            "user": request.user
            }

        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ContextsTasksDetail(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, alias, tsk_id):
        context = Context.get_with_permission(slash_remove(alias), request.user)
        defaults = {
            "id": literal_eval(tsk_id),
            "model_type_alias": context.alias.handle,
            "model_type": "Context"
            }
        task = Task.get_with_permission(defaults, request.user)
        return JsonResponse(task.detail_renderer, safe=False)
