import json
# from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
# from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.shortcuts import redirect
from django.apps import apps
from django.urls import reverse

# from onegeo_manager.context import Context as OnegeoContext
# from onegeo_manager.context import PropertyColumn as OnegeoPropertyColumn
# from onegeo_manager.index import Index as OnegeoIndex
# from onegeo_manager.resource import Resource as OnegeoResource
# from onegeo_manager.source import Source as OnegeoSource

# from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import Alias
from onegeo_api.models import Context
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import on_http403
from onegeo_api.utils import on_http404
from onegeo_api.utils import slash_remove


# def iter_flt_from_anl(anl_name):
#     AnalyserFilters = Analyzer.filter.through
#     set = AnalyserFilters.objects.filter(analyzer__name=anl_name).order_by("id")
#     return [s.filter.name for s in set if s.filter.name is not None]


@method_decorator(csrf_exempt, name="dispatch")
class Action(View):

    # def _retreive_analysis(self, analyzers):
    #
    #     analysis = {'analyzer': {}, 'filter': {}, 'tokenizer': {}}
    #
    #     for analyzer_name in analyzers:
    #         analyzer = Analyzer.objects.get(name=analyzer_name)
    #
    #         plug_anal = analyzer.filter.through
    #         if analyzer.reserved:
    #             if plug_anal.objects.filter(analyzer__name=analyzer_name) and analyzer.tokenizer:
    #                 pass
    #             else:
    #                 continue
    #
    #         if analyzer.config:
    #             analysis['analyzer'][analyzer.name] = analyzer.config
    #             continue
    #
    #         analysis['analyzer'][analyzer.name] = {'type': 'custom'}
    #
    #         tokenizer = analyzer.tokenizer
    #
    #         if tokenizer:
    #             analysis['analyzer'][analyzer.name]['tokenizer'] = tokenizer.name
    #             if tokenizer.config:
    #                 analysis['tokenizer'][tokenizer.name] = tokenizer.config
    #
    #         filters_name = iter_flt_from_anl(analyzer.name)
    #
    #         for filter_name in iter(filters_name):
    #             filter = Filter.objects.get(name=filter_name)
    #             if filter.config:
    #                 analysis['filter'][filter.name] = filter.config
    #
    #         analysis['analyzer'][analyzer.name]['filter'] = filters_name
    #
    #     return analysis
    #
    # def _retreive_analyzers(self, context):
    #
    #     analyzers = []
    #     for prop in context.iter_properties():
    #         if prop.analyzer not in analyzers:
    #             analyzers.append(prop.analyzer)
    #         if prop.search_analyzer not in analyzers:
    #             analyzers.append(prop.search_analyzer)
    #     return [analyzer for analyzer in analyzers if analyzer not in (None, '')]

    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    @ContentTypeLookUp()
    def post(self, request):
        user = request.user

        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            return JsonResponse({'error': e}, status=400)

        ctx_alias = data.get("index")
        if not ctx_alias:
            data = {"error": "L'identifiant du context est manquant "}
            return JsonResponse(data, status=400)

        context = Context.get_with_permission(ctx_alias, request.user)

        filters = {"model_type": "Context", "model_type_alias": context.alias.handle, "user": user}
        last = Task.objects.filter(**filters).order_by("start_date").last()
        if last and last.success is None:
            data = {"error": "Une autre tâche est en cours d'exécution. "
                             "Veuillez réessayer plus tard. "}
            return JsonResponse(data, status=423)

        # # TODO(mmeliani): relation entre context et Resource
        # action = data["type"]

        # rscr = ctx.resource
        # src = rscr.source
        #
        # try:
        #     onegeo_source = OnegeoSource(src.uri, src.name, src.mode)
        # except ConnectionError:
        #     return JsonResponse({'error': 'La source de données est inaccessible.'}, status=404)
        # onegeo_resource = OnegeoResource(onegeo_source, rscr.name)
        # for column in iter(rscr.columns):
        #     if onegeo_resource.is_existing_column(column["name"]):
        #         continue
        #     onegeo_resource.add_column(
        #         column["name"], column_type=column["type"],
        #         occurs=tuple(column["occurs"]), count=column["count"],
        #         rule="rule" in column and column["rule"] or None)
        #
        # onegeo_index = OnegeoIndex(rscr.name)
        # onegeo_context = OnegeoContext(ctx.name, onegeo_index, onegeo_resource)
        #
        # for col_property in iter(ctx.clmn_properties):
        #     context_name = col_property.pop('name')
        #     onegeo_context.update_property(
        #         context_name, 'alias', col_property['alias'])
        #     onegeo_context.update_property(
        #         context_name, 'type', col_property['type'])
        #     onegeo_context.update_property(
        #         context_name, 'pattern', col_property['pattern'])
        #     onegeo_context.update_property(
        #         context_name, 'occurs', col_property['occurs'])
        #     onegeo_context.update_property(
        #         context_name, 'rejected', col_property['rejected'])
        #     onegeo_context.update_property(
        #         context_name, 'searchable', col_property['searchable'])
        #     onegeo_context.update_property(
        #         context_name, 'weight', col_property['weight'])
        #     onegeo_context.update_property(
        #         context_name, 'analyzer', col_property['analyzer'])
        #     onegeo_context.update_property(
        #         context_name, 'search_analyzer', col_property['search_analyzer'])
        #
        # opts = {}
        #
        # if src.mode == "pdf":
        #     pipeline = "attachment"
        #     elastic_conn.create_pipeline_if_not_exists(pipeline)
        #     opts.update({"pipeline": pipeline})
        #
        # if action == "rebuild":
        #     opts.update({"collections": onegeo_context.get_collection()})
        #
        # if action == "reindex":
        #     pass  # Action par défaut
        #
        # # TODO(mmeliani): check _retreive_analysis() & _retreive_analyzers
        # empty_data = {'analyzer': {}, 'filter': {}, 'tokenizer': {}}
        # body = {'mappings': onegeo_context.generate_elastic_mapping(),
        #         'settings': {'analysis': empty_data}}
        #             # 'analysis': self._retreive_analysis(
        #             #     self._retreive_analyzers(onegeo_context))}}
        #
        # index_uuid = str(uuid4())[0:7]
        #
        # description = ("Les données sont en cours d'indexation "
        #                "(id de l'index: '{0}'). ").format(index_uuid)
        # tsk = Task.objects.create(model_type="Context", description=description,
        #                           user=user, model_type_id=ctx.uuid)
        #
        # def on_index_error(desc):
        #     pass
        #
        # def on_index_success(desc):
        #     tsk.success = True
        #     tsk.stop_date = timezone.now()
        #     tsk.description = desc
        #     tsk.save()
        #
        # def on_index_failure(desc):
        #     tsk.success = False
        #     tsk.stop_date = timezone.now()
        #     tsk.description = desc
        #     tsk.save()
        #
        # opts.update({"error": on_index_error,
        #              "failed": on_index_failure,
        #              "succeed": on_index_success})
        #
        # elastic_conn.create_or_replace_index(
        #     index_uuid, ctx.name, ctx.name, body, **opts)
        #
        # status = 202
        # data = {"message": tsk.description}

        # return JsonResponse(data, status=status)
        return JsonResponse({"Tomatoe": "Tomatoe"}, status=418)


@method_decorator(csrf_exempt, name="dispatch")
class AliasDetail(View):
    @BasicAuth()
    @ExceptionsHandler(
        actions={Http404: on_http404, PermissionDenied: on_http403})
    def get(self, request, alias):

        user = request.user
        alias_instance = Alias.get_with_permission(slash_remove(alias))
        path = {
            "Analyzer": "onegeo_api:analyzers_detail",
            "Source": "onegeo_api:sources_detail",
            "Resource": "onegeo_api:resources_detail",
            "Context": "onegeo_api:indexes_detail",
            "Filter": "onegeo_api:tokenfilters",
            "Tokenizer": "onegeo_api:tokenizer",
            "SearchModel": "onegeo_api:seamod_detail"
            }

        Model_r = apps.get_model(app_label='onegeo_api', model_name=alias_instance.model_name)
        instance = Model_r.get_with_permission(alias_instance.handle, user)
        namespace = path.get(alias_instance.model_name)
        if alias_instance.model_name == "Resource":
            kwargs = {'src_alias': instance.source.alias.handle, 'rsrc_alias': instance.alias.handle}
        else:
            kwargs = {'alias': instance.alias.handle}
        return redirect(reverse(namespace, kwargs=kwargs))


@method_decorator(csrf_exempt, name="dispatch")
class Bulk(View):
        @BasicAuth()
        @ContentTypeLookUp()
        @ExceptionsHandler(
            actions={Http404: on_http404, PermissionDenied: on_http403})
        def post(self, request):

            user = request.user
            body_data = json.loads(request.body.decode('utf-8'))
            """
                {
                    "post": [
                        {
                            "model_name": {"body_data_create_key": "body_data_create_value"},
                            "model_name_2": {"body_data_create_key": "body_data_create_value"}
                            }],
                    "put": [
                        {
                            "alias_1": {"body_data_update_key": "body_data_update_value"},
                            "alias_2": {"body_data_update_key": "body_data_update_value"}
                        }
                     ],
                     "delete": [ "alias_1", "alias_2"]
                }

            """
            # Creation de sources / resources
            for post_requested in body_data.get("post", []):
                for source in post_requested.get("sources", []):
                    print(source)
            # Création de contexts

            return JsonResponse({}, status=200)
