from ast import literal_eval
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
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
from onegeo_api.models import Context
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove

__all__ = ["ContextView", "ContextIDView",
           "ContextIDTaskView", "ContextIDTaskIDView"]

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


@method_decorator(csrf_exempt, name="dispatch")
class ContextView(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Context.list_renderer(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Context")
    def post(self, request):
        body_data = json.loads(request.body.decode('utf-8'))
        if "name" not in body_data:
            return JsonResponse({"error": "Echec la création du contexte d'indexation. "
                                          "Le nom du contexte est manquant. "}, status=400)
        if "resource" not in body_data:
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
            src_uuid = data.group(1)
            rsrc_uuid = data.group(2)

            resource = Resource.get_with_permission(rsrc_uuid, request.user)
            source = Source.get_with_permission(src_uuid, request.user)

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

        return Context.create_with_response(
            request, name, clmn_properties, reindex_frequency, resources_to_relate)


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDView(View):

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Context")
    def get(self, request, uuid):
        context = Context.get_with_permission(slash_remove(uuid), request.user)
        return JsonResponse(context.detail_renderer, safe=False, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403},
        model="Various")
    def put(self, request, ctx_uuid):

        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = body_data.get('name')
        reindex_frequency = body_data.get('reindex_frequency')
        list_ppt_clt = body_data.get('columns', {})

        data = search('^/sources/(\S+)/resources/(\S+)$', body_data['resource'])
        if not data:
            return None
        src_uuid = data.group(1)
        rsrc_uuid = data.group(2)

        resource = Resource.get_with_permission(rsrc_uuid, request.user)
        source = Source.get_with_permission(src_uuid, request.user)

        if source != resource.source:
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Les identifiants des source et ressource sont erronées. "}, status=400)

        context = Context.get_with_permission(slash_remove(ctx_uuid), request.user)

        context.update_clmn_properties(list_ppt_clt)

        context.resources.add(resource)
        if name:
            context.name = name
        if reindex_frequency:
            context.reindex_frequency = reindex_frequency
        context.save()

        return JsonResponse(data={}, status=204)

    @BasicAuth()
    def delete(self, request, uuid):
        return Context.delete_with_response(slash_remove(uuid), request.user)


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDTaskView(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403}, model="Context")
    def get(self, request, ctx_uuid):

        context = Context.get_with_permission(slash_remove(ctx_uuid), request.user)
        tasks = Task.objects.filter(
            model_type="context",
            model_type_id=context.uuid,
            user=request.user).order_by("-start_date")

        return JsonResponse([task.detail_renderer for task in tasks], safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDTaskIDView(View):

    @BasicAuth()
    @ExceptionsHandler(actions={Http404: on_http404, PermissionDenied: on_http403}, model="Various")
    def get(self, request, ctx_uuid, tsk_id):

        context = Context.get_with_permission(slash_remove(ctx_uuid), request.user)
        task = get_object_or_404(
            Task, pk=literal_eval(tsk_id), model_type_id=context.uuid)

        return JsonResponse(task.detail_renderer, safe=False)
