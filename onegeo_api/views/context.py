import json
from ast import literal_eval
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from re import search
from onegeo_manager.context import Context as OnegeoContext
from onegeo_manager.index import Index as OnegeoIndex
from onegeo_manager.resource import Resource as OnegeoResource
from onegeo_manager.source import Source as OnegeoSource

from ..models import Context, Resource, Source, Task
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import read_name
from onegeo_api.utils import slash_remove

__all__ = ["ContextView", "ContextIDView",
           "ContextIDTaskView", "ContextIDTaskIDView"]


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR
MSG_406 = "Le format demandé n'est pas pris en charge. "
MSG_404 = {
    "GetResource": {"error": "Aucune resource ne correspond à cette requête."},
    "GetContext": {"error": "Aucun context ne correspond à cette requête."}}

# def check_columns(list_ppt, list_ppt_clt):
#     for ppt in list_ppt:
#         for ppt_clt in list_ppt_clt:
#             if ppt["name"] == ppt_clt["name"]:
#                 ppt.update(ppt_clt)
#     return list_ppt


@method_decorator(csrf_exempt, name="dispatch")
class ContextView(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(Context.format_by_filter(request.user), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
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
        if Context.objects.filter(name=name).count() > 0:
            return JsonResponse({"error": "Echec de création du contexte d'indexation. "
                                          "Un contexte portant le même nom existe déjà. "}, status=409)

        reindex_frequency = body_data.get("reindex_frequency", "monthly")

        data = search('^/sources/(\S+)/resources/(\S+)$', body_data['resource'])
        if not data:
            return None
        # src_uuid = data.group(1)
        rsrc_uuid = data.group(2)

        resource = Resource.get_from_uuid(rsrc_uuid, request.user)
        if not resource:
            return JsonResponse(MSG_404["GetResource"], status=404)
        source = resource.source

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
        column_ppt = []
        for property in onegeo_context.iter_properties():
            column_ppt.append(property.all())

        try:
            context = Context.objects.create(name=name,
                                             clmn_properties=column_ppt,
                                             reindex_frequency=reindex_frequency)
        except ValidationError as e:
            return JsonResponse(data={"error": e.message}, status=409)
        context.resources.add(resource)
        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{}/{}'.format(uri, context.uuid)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDView(View):

    @BasicAuth()
    def get(self, request, uuid):
        context = Context.get_from_uuid(uuid, request.user)
        if not context:
            return JsonResponse(MSG_404["GetContext"], status=404)

        return JsonResponse(context.format_data, safe=False, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    def put(self, request, uuid):

        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        # if "name" in body_data:
        #     name = body_data['name']
        name = body_data.get('name')

        # reindex_frequency = None
        # if "reindex_frequency" in body_data:
        #     reindex_frequency = body_data['reindex_frequency']
        reindex_frequency = body_data.get('reindex_frequency')

        # list_ppt_clt = {}
        # if "columns" in body_data:
        #     list_ppt_clt = body_data['columns']
        list_ppt_clt = body_data.get('columns', {})

        data = search('^/sources/(\S+)/resources/(\S+)$', body_data['resource'])
        if not data:
            return None
        # src_id = data.group(1)
        rsrc_uuid = data.group(2)

        resource = Resource.get_from_uuid(rsrc_uuid, request.user)
        if not resource:
            return JsonResponse(MSG_404["GetResource"], status=404)

        context = Context.get_from_uuid(uuid, request.user)
        if not context:
            return JsonResponse(MSG_404["GetContext"], status=404)

        # list_ppt = context.clmn_properties
        # ppt_update = check_columns(list_ppt, list_ppt_clt)
        # context.clmn_properties = ppt_update
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
        user = request.user

        id = literal_eval(id)

        return utils.delete_func(id, user(), Context)


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDTaskView(View):

    def get(self, request, id):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        ctx_id = literal_eval(id)

        get_object_or_404(Context, pk=ctx_id)

        set = Task.objects.filter(model_type="context",
                                  model_type_id=ctx_id,
                                  user=user()).order_by("-start_date")

        data = [utils.format_task(tsk) for tsk in set]

        return JsonResponse(data, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDTaskIDView(View):

    def get(self, request, ctx_id, tsk_id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        tsk_id = literal_eval(tsk_id)
        tsk = get_object_or_404(Task, pk=tsk_id, model_type_id=ctx_id)

        return JsonResponse(utils.format_task(tsk), safe=False)
