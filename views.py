from ast import literal_eval
from re import search
from uuid import uuid4

from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from .models import Source, Resource, Context, Filter, Analyzer, Tokenizer, SearchModel
from django.conf import settings
from django.db import transaction


from onegeo_manager.source import PdfSource
from onegeo_manager.index import Index
from onegeo_manager.context import PdfContext

import json

from . import utils

from .elasticsearch_wrapper import elastic_conn

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR

@method_decorator(csrf_exempt, name="dispatch")
class SourceView(View):

    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Source), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            data = {"error": "Content-type incorrect"}
            return JsonResponse(data, status=406)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        field_missing = False
        if "uri" not in body_data:
            data = {"error": "URI field is missing"}
            field_missing = True
        if "mode" not in body_data:
            data = {"error": "Mode field is missing"}
            field_missing = True
        if "name" not in body_data:
            data = {"error": "Name field is missing"}
            field_missing = True
        if field_missing is True:
            return JsonResponse(data, status=400)

        uri = body_data["uri"]
        mode = body_data["mode"]
        name = body_data["name"]

        np = utils.check_uri(uri)
        if np is None:
            data = {"error":"Chemin de l'URI incorrect"}
            return JsonResponse(data, status=400)

        sources, created = Source.objects.get_or_create(uri=np, user=user(), name=name, mode=mode)
        status = created and 201 or 409

        if created:
            response = JsonResponse(data={}, status=status)
            response['Location'] = '{}{}'.format(request.build_absolute_uri(), sources.id)
        if created is False:
            data = {"error": "Conflict"}
            response = JsonResponse(data=data, status=status)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class SourceIDView(View):

    def get(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        src_id = literal_eval(id)
        return JsonResponse(utils.get_object_id(user(), src_id, Source), safe=False)

    def delete(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        src_id = literal_eval(id)

        source = Source.objects.filter(id=src_id, user=user())
        if len(source) == 1:
            source.delete()
            data = {"message":"Success"}
            status = 200
        elif len(source) == 0:
            src = Source.objects.filter(id=src_id)
            if len(src) == 1:
                data = {"error": "Forbidden"}
                status = 403
            elif len(src) == 0:
                data = {"message":"No Content"}
                status = 204
        return JsonResponse(data, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ResourceView(View):

    def get(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        src_id = literal_eval(id)
        return JsonResponse(utils.get_objects(user(), Resource, src_id), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ResourceIDView(View):

    def get(self, request, src_id, rsrc_id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_object_id(user(), rsrc_id, Resource, src_id), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ContextView(View):


    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Context), safe=False)


    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse({"error": "Content-type incorrect"}, status=406)

        body_data = json.loads(request.body.decode('utf-8'))
        if "name" not in body_data:
            return JsonResponse({"error": "Name field is missing"}, status=400)
        if "resource" not in body_data:
            return JsonResponse({"error": "Resource field is missing"}, status=400)

        name = body_data['name']
        if Context.objects.filter(name = name).count() > 0:
            return JsonResponse({"error": "Le nom d'un context doit etre unique"}, status=409)

        reindex_frequency = "monthly"
        if "reindex_frequency" in body_data:
            reindex_frequency = body_data['reindex_frequency']

        data = search('^\/sources\/(\d+)\/resources\/(\d+)$', body_data['resource'])
        if not data:
            return None
        src_id = data.group(1)
        rsrc_id = data.group(2)
        set_src = get_object_or_404(Source, id=src_id)

        set_rscr = get_object_or_404(Resource, source=set_src, id=rsrc_id)
        if Context.objects.filter(resource__id = rsrc_id).count() > 0:
            return JsonResponse({"error": "Cette resource est déja liée à un context"}, status=409)

        pdf = PdfSource(set_src.uri, name, set_src.mode)
        type = None
        index = Index(set_rscr.name)
        for e in iter(pdf.get_types()):
            if e.name == set_rscr.name:
                type = e
        context = PdfContext(index, type)
        column_ppt = []
        for property in context.iter_properties():
            column_ppt.append(property.all())


        context = Context.objects.create(resource=set_rscr,
                                         name=name,
                                         clmn_properties=column_ppt,
                                         reindex_frequency=reindex_frequency)

        response = JsonResponse(data={}, status=201)
        response['Location'] = '{}{}'.format(request.build_absolute_uri(), context.resource_id)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDView(View):

    def get(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        ctx_id = literal_eval(id)
        return JsonResponse(utils.get_object_id(user(), ctx_id, Context), safe=False)

    def put(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        if "name" in body_data:
            name = body_data['name']

        reindex_frequency = None
        if "reindex_frequency" in body_data:
            reindex_frequency = body_data['reindex_frequency']

        list_ppt_clt = {}
        if "columns" in body_data:
            list_ppt_clt = body_data['columns']

        data = search('^\/sources\/(\d+)\/resources\/(\d+)$', body_data['resource'])
        if not data:
            return None
        src_id = data.group(1)
        rsrc_id = data.group(2)
        set_src = get_object_or_404(Source, id=src_id)
        set_rscr = get_object_or_404(Resource, source=set_src, id=rsrc_id)

        ctx_id = literal_eval(id)
        context = get_object_or_404(Context, resource_id=ctx_id)

        list_ppt = context.clmn_properties
        ppt_update = utils.check_columns(list_ppt, list_ppt_clt)

        if reindex_frequency:
            context.update(resource=set_rscr,
                           name=name,
                           clmn_properties=ppt_update,
                           reindex_frequency=reindex_frequency)
        else:
            context.update(resource=set_rscr,
                           name=name,
                           clmn_properties=ppt_update)

        return JsonResponse(data={}, status=200)

    def delete(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        ctx_id = literal_eval(id)
        context = Context.objects.filter(resource_id=ctx_id, resource__source__user=user())

        if len(context) == 1:
            context.delete()
            status = 200
            data = {}
        elif len(context) == 0:
            ctx = Context.objects.filter(resource_id=ctx_id)
            if len(ctx) == 1:
                status = 403
                data = {"error": "Forbidden"}
            elif len(ctx) == 0:
                data = {"message":"no content"}
                status = 204
        return JsonResponse(data, status=status)

@method_decorator(csrf_exempt, name="dispatch")
class FilterView(View):

    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Filter), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = utils.read_name(body_data)
        if name is None:
            return HttpResponseBadRequest()

        cfg = "config" in body_data and body_data["config"] or {}

        filter, created = Filter.objects.get_or_create(config=cfg, user=user(), name=name)
        status = created and 201 or 409

        if created:
            response = JsonResponse(data={}, status=status)
            response['Location'] = '{}{}'.format(request.build_absolute_uri(), filter.name)
        if created is False:
            data = {"error": "Conflict"}
            response = JsonResponse(data=data, status=status)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class FilterIDView(View):

    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        return JsonResponse(utils.get_object_id(user(), name, Filter))

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        cfg = "config" in body_data and body_data["config"] or {}

        flt_name = (name.endswith('/') and name[:-1] or name)
        filter = Filter.objects.filter(name=flt_name, user=user())

        if len(filter) == 1:
            filter.update(config=cfg)
            status = 200
            data = {}
        elif len(filter) == 0:
            flt = Filter.objects.filter(name=flt_name)
            if len(flt) == 1:
                status = 403
                data = {"error":"Forbidden"}
            elif len(flt) == 0:
                status = 204
                data = {"message":"No content"}

        return JsonResponse(data, status=status)


    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        name = (name.endswith('/') and name[:-1] or name)
        filter = Filter.objects.filter(name=name, user=user())

        if len(filter) == 1:
            filter = filter[0]
            if not filter.reserved:
                filter.delete()
                status = 200
                data = {}
            else:
                status = 405
                data = {"error":"Not Allowed"}
        elif len(filter) == 0:
            flt = Filter.objects.filter(name=name)
            if len(flt) == 1:
                status = 403
                data = {"error":"Forbidden"}
            elif len(flt) == 0:
                status = 204
                data = {"message":"No content"}
        else:
            return HttpResponseBadRequest()

        return JsonResponse(data, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerView(View):
    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Analyzer), safe=False)

    @transaction.atomic
    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = utils.read_name(body_data)
        if name is None:
            return HttpResponseBadRequest()

        tokenizer = "tokenizer" in body_data and body_data["tokenizer"] or None
        filters = "filters" in body_data and body_data["filters"] or []

        analyzer, created = Analyzer.objects.get_or_create(user=user(), name=name)
        if created and len(filters) > 0:
            for f in filters:
                try:
                    flt = Filter.objects.get(name=f)
                    analyzer.filter.add(flt)
                    analyzer.save()
                except Filter.DoesNotExist:
                    return JsonResponse({"error":"Filter DoesNotExist"}, status=400)

        if created and tokenizer is not None:
            try:
                tkn_chk = Tokenizer.objects.get(name=tokenizer)
                analyzer.tokenizer = tkn_chk
                analyzer.save()
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error":"Tokenizer DoesNotExist"}, status=400)
        status = created and 201 or 409

        if created:
            response = JsonResponse(data={}, status=status)
            response['Location'] = '{}{}'.format(request.build_absolute_uri(), analyzer.name)
        if created is False:
            data = {"error": "Conflict"}
            response = JsonResponse(data=data, status=status)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerIDView(View):
    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/')and name[:-1] or name)
        return JsonResponse(utils.get_object_id(user(), name, Analyzer))

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        tokenizer = "tokenizer" in body_data and body_data["tokenizer"] or False
        filters = "filters" in body_data and body_data["filters"] or []

        name = (name.endswith('/') and name[:-1] or name)
        analyzer = get_object_or_404(Analyzer, name=name)

        if tokenizer:
            try:
                tkn_chk = Tokenizer.objects.get(name=tokenizer)
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error":"Echec de la mise à jour Analyseur: Tokenizer DoesNotExist"}, status=400)

        if analyzer.user != user():
            status = 403
            data = {"error": "Forbidden"}
        else:
            status = 200
            data = {}
            if len(filters) > 0:
                for f in filters:                  
                    try:
                        flt = Filter.objects.get(name=f)
                    except Filter.DoesNotExist:
                        return JsonResponse({"error":"Echec de la mise à jour Analyseur: Filter DoesNotExist"}, status=400)

                analyzer.filter.set([])
                for f in filters:
                    analyzer.filter.add(f)
                analyzer.save()
            if tokenizer:
                analyzer.tokenizer = tkn_chk
                analyzer.save()

        return JsonResponse(data, status=status)

    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)

        analyzer = get_object_or_404(Analyzer, name=name)
        response = HttpResponse()

        if analyzer.reserved:
            response.status_code = 403
            return response

        if analyzer.user == user():
            status = 200
            analyzer.delete()

        elif analyzer.user != user():
            status = 403
        else:
            return HttpResponseBadRequest()
        response.status_code = status
        return response


@method_decorator(csrf_exempt, name="dispatch")
class TokenizerView(View):

    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_objects(user(), Tokenizer), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = utils.read_name(body_data)
        if name is None:
            return HttpResponseBadRequest()
        cfg = "config" in body_data and body_data["config"] or {}
        token, created = Tokenizer.objects.get_or_create(config=cfg, user=user(), name=name)
        status = created and 201 or 409
        response = HttpResponse()
        response.status_code = status
        if created:
            response['Location']  = '{}{}'.format(request.build_absolute_uri(), token.name)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class TokenizerIDView(View):

    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        return JsonResponse(utils.get_object_id(user(), name, Tokenizer), safe=False)

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        cfg = "config" in body_data and body_data["config"] or {}

        name = (name.endswith('/') and name[:-1] or name)
        token = Tokenizer.objects.filter(name=name, user=user())

        if len(token) == 1:
            token.update(config=cfg)
            status = 200
            data = {}
        elif len(token) == 0:
            status = 204
            data = {"message":"No content"}

        return JsonResponse(data, status=status)


    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)


        token = Tokenizer.objects.filter(name=name, user=user())

        if len(token) == 1:
            token = token[0]
            if not token.reserved:
                token.delete()
                status = 200
                data = {}
            else:
                status = 405
                data = {"error": "Not Allowed"}

        elif len(token) == 0:
            flt = Filter.objects.filter(name=name)
            if len(flt) == 1:
                status = 403
                data = {"error": "Forbidden"}
            elif len(flt) == 0:
                status = 204
                data = {"message"}

        return JsonResponse


@method_decorator(csrf_exempt, name="dispatch")
class Directories(View):

    def get(self, request):
        user = utils.UserAuthenticate(request)
        if user() is None:
            response = HttpResponse()
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="%s"' % "Basic Auth Protected"
            return response

        subdir = utils.uri_shortcut(PDF_BASE_DIR)

        return JsonResponse(subdir, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ActionView(View):

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        data = json.loads(request.body.decode("utf-8"))

        try:
            ctx = Context.objects.get(name=data["index"])
        except Context.DoesNotExist:
            return HttpResponseBadRequest()

        action = data["type"]

        rscr = ctx.resource
        src = rscr.source

        pdf = PdfSource(src.uri, src.name, src.mode)

        doc_type = None
        index = Index(rscr.name)
        for e in iter(pdf.get_types()):
            if e.name == rscr.name:
                doc_type = e

        context = PdfContext(index, doc_type)

        for col_property in iter(ctx.clmn_properties):
            context.update_property(**col_property)

        opts = {}

        if src.mode == "pdf":
            pipeline = "attachment"
            elastic_conn.create_pipeline_if_not_exists(pipeline)
            opts.update({"pipeline": pipeline})

        if action == "rebuild":
            opts.update({"collections": context.get_collection()})
        
        if action == "reindex":
            pass  # Action par défaut
        
        body = {'mappings': context.generate_elastic_mapping(),
                'settings': {
                    'analysis': self.retreive_analysis(
                                        self.retreive_analyzers(context))}}

        elastic_conn.create_or_replace_index(str(uuid4())[0:7],  # Un UUID comme nom d'index
                                             ctx.name,           # Alias de l'index
                                             doc_type.name,      # Nom du type
                                             body,               # Settings & Mapping
                                             **opts)

        response = HttpResponse()
        response.status_code = 202. # Ne garantie pas un résultat
        return response

    def retreive_analyzers(self, context):

        analyzers = []
        for prop in context.iter_properties():
            if prop.analyzer not in analyzers:
                analyzers.append(prop.analyzer)
            if prop.search_analyzer not in analyzers:
                analyzers.append(prop.search_analyzer)
        return [analyzer for analyzer in analyzers if analyzer not in (None, '')]

    def retreive_analysis(self, analyzers):

        analysis = {'analyzer': {}, 'filter': {}, 'tokenizer': {}}

        for analyzer_name in analyzers:
            analyzer = Analyzer.objects.get(name=analyzer_name)

            if analyzer.reserved:
                continue

            analysis['analyzer'][analyzer.name] = {'type': 'custom'}

            tokenizer = analyzer.tokenizer
            if tokenizer:
                analysis['analyzer'][analyzer.name]['tokenizer'] = tokenizer.name
                if not tokenizer.reserved:
                    analysis['tokenizer'][tokenizer.name] = tokenizer.config

            filters_name = utils.iter_flt_from_anl(analyzer.name)
            for filter_name in iter(filters_name):
                filter = Filter.objects.get(name=filter_name)
                if not filter.reserved:
                    analysis['filter'][filter.name] = filter.config
            
            analysis['analyzer'][analyzer.name]['filter'] = filters_name

        return analysis


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
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = utils.read_name(body_data)
        if name is None:
            return HttpResponseBadRequest()

        cfg = "config" in body_data and body_data["config"] or {}
        ctx = "contexts" in body_data and body_data["contexts"] or []

        created = False
        response = HttpResponse()

        try:
            search_model, created = SearchModel.objects.get_or_create(config=cfg, user=user(), name=name)
        except ValidationError as err:
            return JsonResponse({"message": err.message}, safe=False, status=409)


        status = created and 201 or 409
        response.status_code = status

        if created:
            search_model.context.clear()
            ctx_clt = []
            if len(ctx) > 0:
                ctx_l = []
                for c in ctx_clt:
                    try:
                        ctx = Context.objects.get(name=c)
                    except Context.DoesNotExist:
                        return HttpResponseBadRequest("Context Does Not Exist")
                    else:
                        ctx_l.append(ctx)
                search_model.context.set(ctx_l)

            response['Location']  = '{}{}'.format(request.build_absolute_uri(), search_model.name)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class SearchModelIDView(View):

    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        res = utils.get_object_id(user(), name, SearchModel)
        if res is None:
            response = JsonResponse({'Error': '401 Unauthorized'})
            response.status_code = 403
        else:
            response = JsonResponse(res)
            response.status_code = 200
        return response

    def put(self, request, name):

        # Check user
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        # Check content-type
        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = (name.endswith('/') and name[:-1] or name)

        ctx_clt = "contexts" in body_data and body_data["contexts"] or []
        config = "config" in body_data and body_data["config"] or {}
        response = HttpResponse()

        # QS filter pour update() config
        search_model = SearchModel.objects.filter(name=name, user=user())
        if len(search_model) == 1:

            # Object SearchModel pour set() context
            sm = get_object_or_404(SearchModel, name=name)

            # Si contexts[] est dans data_body
            if len(ctx_clt) > 0:
                sm.context.clear()
                ctx_l = []
                for c in ctx_clt:
                    try:
                        # Check si les contexts sont correct
                        ctx = Context.objects.get(name=c)
                    except Context.DoesNotExist:
                        return HttpResponseBadRequest("Context Does Not Exist")
                    else:
                        ctx_l.append(ctx)
                # Object SearchModel contiendra la nouvelle liste de contexts
                sm.context.set(ctx_l)

            search_model.update(config=config)
            status = 200
            message = "OK: Requête traitée avec succès."

        elif len(search_model) == 0:
            mdl = SearchModel.objects.filter(name=name)

            if len(mdl) == 1:
                status = 403
                message = "Forbidden: Vous n'avez pas les permissions necessaires à l'acces de cette resource"

            elif len(mdl) == 0:
                status = 204
                message = "No Content: Requête traitée avec succès mais pas d’information à renvoyer."

        body = {'actions': []}

        for index in elastic_conn.get_indices_by_alias(name=name):
            body['actions'].append({'remove': {'index': index, 'alias': name}})

        for context in iter(ctx_clt):
            for index in elastic_conn.get_indices_by_alias(name=context):
                body['actions'].append({'add': {'index': index, 'alias': name}})

        if not elastic_conn.is_a_task_running():
            elastic_conn.update_aliases(body)
        else:
            status = 423
            message = "Locked: L'acces à la ressource est impossible"

        response.status_code = status
        data = {"message": message}
        return JsonResponse(data, status=status)

    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        response = HttpResponse()
        name = (name.endswith('/') and name[:-1] or name)
        search_model = SearchModel.objects.filter(name=name, user=user())

        if len(search_model) == 1:
            search_model[0].delete()
            response.status_code = 200

        elif len(search_model) == 0:
            mdl = SearchModel.objects.filter(name=name)
            if len(mdl) == 1:
                response.status_code = 403
                response.content = "Forbidden: Vous n'avez pas les permissions necessaires à l'acces de cette resource"
            elif len(mdl) == 0:
                response.status_code = 204
        else:
            return HttpResponseBadRequest()

        return response

@method_decorator(csrf_exempt, name="dispatch")
class SearchView(View):

    def get_param(self, request, param):
        """
            Retourne la valeur d'une clé param presente dans une requete GET ou POST
        """
        if request.method == 'GET':
            if param in request.GET:
                return request.GET[param]
        elif request.method == 'POST':
            try:
                param_read = request.POST.get(param, request.GET.get(param))
            except KeyError as e:
                return None
            return param_read

    def post(self, request, name):

        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        model = SearchModel.objects.filter(name=name)

        data = request.body.decode('utf-8')

        mode = self.get_param(request, 'mode')
        if mode == 'throw':
            data = elastic_conn.search(index=name, body=data)
            if data:
                return JsonResponse(data=data, safe=False, status=200)
        else:
            return JsonResponse(data={'message': 'todo'}, safe=False, status=501)