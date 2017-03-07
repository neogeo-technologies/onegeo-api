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
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        if "uri" not in body_data:
            return JsonResponse([{"Error": "URI field is missing"}], safe=False)
        if "mode" not in body_data:
            return JsonResponse([{"Error": "Mode field is missing"}], safe=False)
        if "name" not in body_data:
            return JsonResponse([{"Error": "Name field is missing"}], safe=False)

        uri = body_data["uri"]
        mode = body_data["mode"]
        name = body_data["name"]

        np = utils.check_uri(uri)
        if np is None:
            return HttpResponseBadRequest()

        sources, created = Source.objects.get_or_create(uri=np, user=user(), name=name, mode=mode)
        status = created and 201 or 409

        response = HttpResponse()
        response.status_code = status
        if created:
            response['Location']  = '{}{}'.format(request.build_absolute_uri(), sources.id)
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
        response = HttpResponse()

        source = Source.objects.filter(id=src_id, user=user())
        if len(source) == 1:
            source.delete()
            response.status_code = 200
        elif len(source) == 0:
            src = Source.objects.filter(id=src_id)
            if len(src) == 1:
                response.status_code = 403
            elif len(src) == 0:
                response.status_code = 204
        return response


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
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')

        body_data = json.loads(data)
        if "name" not in body_data:
            return JsonResponse([{"Error": "Name field is missing"}], safe=False)
        if "resource" not in body_data:
            return JsonResponse([{"Error": "Resource field is missing"}], safe=False)

        name = body_data['name']

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

        ctx = Context.objects.filter(resource=set_rscr)
        response = HttpResponse()
        created = False

        if len(ctx) == 0:
            try:
                new_context = Context.objects.create(resource=set_rscr,
                                                 name=name,
                                                 clmn_properties=column_ppt,
                                                 reindex_frequency=reindex_frequency)
                status = 201
                created = True
            except ValidationError as err:
                response.content = err
                status = 409
        if len(ctx) == 1:
            response.content = "La requête ne peut être traitée en l’état actuel."
            status = 409

        response.status_code = status
        if created:
            response['Location'] = '{}{}'.format(request.build_absolute_uri(), new_context.resource_id)
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

        name = body_data['name']

        reindex_frequency = "monthly"
        if "reindex_frequency" in body_data:
            reindex_frequency = body_data['reindex_frequency']

        column_ppt = body_data['columns']

        data = search('^\/sources\/(\d+)\/resources\/(\d+)$', body_data['resource'])
        if not data:
            return None
        src_id = data.group(1)
        rsrc_id = data.group(2)
        set_src = get_object_or_404(Source, id=src_id)
        set_rscr = get_object_or_404(Resource, source=set_src, id=rsrc_id)

        ctx_id = literal_eval(id)
        context = Context.objects.filter(resource_id=ctx_id)
        
        if len(context) == 1:
            context.update(resource=set_rscr, 
                           name=name, 
                           clmn_properties=column_ppt,
                           reindex_frequency=reindex_frequency)

            status = 200
        elif len(context) == 0:
            status = 204
        response = HttpResponse()
        response.status_code = status
        return response

    def delete(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        ctx_id = literal_eval(id)
        response = HttpResponse()
        context = Context.objects.filter(resource_id=ctx_id, resource__source__user=user())
        if len(context) == 1:
            context.delete()
            response.status_code = 200
        elif len(context) == 0:
            ctx = Context.objects.filter(resource_id=ctx_id)
            if len(ctx) == 1:
                response.status_code = 403
            elif len(ctx) == 0:
                response.status_code = 204
        return response

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
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = utils.read_name(body_data)
        if name is None:
            return HttpResponseBadRequest()

        cfg = "config" in body_data and body_data["config"] or {}

        filter, created = Filter.objects.get_or_create(config=cfg, user=user(), name=name)
        status = created and 201 or 409
        response = HttpResponse()
        response.status_code = status
        if created:
            response['Location']  = '{}{}'.format(request.build_absolute_uri(), filter.name)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class FilterIDView(View):

    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        res = utils.get_object_id(user(), name, Filter)
        if res is None:
            response = JsonResponse({'Error': '401 Unauthorized'})
            response.status_code = 403
        else:
            response = JsonResponse(res)
            response.status_code = 200
        return response

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        cfg = "config" in body_data and body_data["config"] or {}

        flt_name = (name.endswith('/') and name[:-1] or name)
        filter = Filter.objects.filter(name=flt_name, user=user())

        if len(filter) == 1:
            filter.update(config=cfg)
            status = 200
        elif len(filter) == 0:
            flt = Filter.objects.filter(name=flt_name)
            if len(flt) == 1:
                status = 403
            elif len(flt) == 0:
                status = 204
        response = HttpResponse()
        response.status_code = status
        return response


    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        response = HttpResponse()
        flt_name = (name.endswith('/') and name[:-1] or name)
        filter = Filter.objects.filter(name=flt_name, user=user())

        if len(filter) == 1:
            filter = filter[0]
            if not filter.reserved:
                filter.delete()
                response.status_code = 200
            else:
                response.status_code = 405
        elif len(filter) == 0:
            flt = Filter.objects.filter(name=flt_name)
            if len(flt) == 1:
                response.status_code = 403
            elif len(flt) == 0:
                response.status_code = 204
        else:
            return HttpResponseBadRequest()

        return response


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
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
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
                    return HttpResponseBadRequest("Filter DoesNotExist")

        if created and tokenizer is not None:
            try:
                tkn_chk = Tokenizer.objects.get(name=tokenizer)
                analyzer.tokenizer = tkn_chk
                analyzer.save()
            except Tokenizer.DoesNotExist:
                return HttpResponseBadRequest("Tokenizer DoesNotExist")
        status = created and 201 or 409
        response = HttpResponse()
        response.status_code = status
        if created:
            response['Location'] = '{}{}'.format(request.build_absolute_uri(), analyzer.name)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AnalyzerIDView(View):
    def get(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/')and name[:-1] or name)

        res = utils.get_object_id(user(), name, Analyzer)
        if res is None:
            response = JsonResponse({'Error': '401 Unauthorized'})
            response.status_code = 403
        else:
            response = JsonResponse(res)
            response.status_code = 200
        return response

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
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
                return HttpResponseBadRequest("Tokenizer DoesNotExist")

        response = HttpResponse()
        if analyzer.user == user():
            status = 200
            if len(filters) > 0:
                for f in filters:                  
                    try:
                        flt = Filter.objects.get(name=f)
                    except Filter.DoesNotExist:
                        return HttpResponseBadRequest("Filter DoesNotExist")
                analyzer.filter.set([])
                for f in filters:
                    analyzer.filter.add(f)
                analyzer.save()
            if tokenizer:
                analyzer.tokenizer = tkn_chk
                analyzer.save()
        elif analyzer.user != user():
            status = 403
        else:
            return HttpResponseBadRequest()
        response.status_code = status
        return response

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
        res = utils.get_object_id(user(), name, Tokenizer)
        if res is None:
            response = JsonResponse({'Error': '401 Unauthorized'})
            response.status_code = 403
        else:
            response = JsonResponse(res)
            response.status_code = 200
        return response

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
        elif len(token) == 0:
            status = 204
        response = HttpResponse()
        response.status_code = status
        return response


    def delete(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        name = (name.endswith('/') and name[:-1] or name)
        response = HttpResponse()

        token = Tokenizer.objects.filter(name=name, user=user())

        if len(token) == 1:
            token = token[0]
            if not token.reserved:
                token.delete()
                response.status_code = 200
            else:
                response.status_code = 405

        elif len(token) == 0:
            flt = Filter.objects.filter(name=name)
            if len(flt) == 1:
                response.status_code = 403
            elif len(flt) == 0:
                response.status_code = 204
        else:
            return HttpResponseBadRequest()
        return response


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
        # response = JsonResponse()

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
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)

        name = (name.endswith('/') and name[:-1] or name)
        # search_model = get_object_or_404(SearchModel, name=name)
        search_model = SearchModel.objects.filter(name=name, user=user())

        ctx_clt = "contexts" in body_data and body_data["contexts"] or []
        config = "config" in body_data and body_data["config"] or {}
        response = HttpResponse()

        if len(search_model) == 1:

            sm = get_object_or_404(SearchModel, name=name)
            sm.context.clear()

            if len(ctx_clt) > 0:
                ctx_l = []
                for c in ctx_clt:
                    try:
                        ctx = Context.objects.get(name=c)
                    except Context.DoesNotExist:
                        return HttpResponseBadRequest("Context Does Not Exist")
                    else:
                        ctx_l.append(ctx)
                sm.context.set(ctx_l)

            search_model.update(config=config)
            status = 200
            message  = "OK: Requête traitée avec succès."

        elif len(search_model) == 0:
            mdl = SearchModel.objects.filter(name=name)

            if len(mdl) == 1:
                status = 403
                message = "Forbidden: Vous n'avez pas les permissions necessaires à l'acces de cette resource"

            elif len(mdl) == 0:
                status = 204
                message = "No Content: Requête traitée avec succès mais pas d’information à renvoyer."



        response.status_code = status
        return JsonResponse([{"Message": message}], safe=False, status=status)
        # return response

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
    def get(self, request, name):
        """Connect config elastic search"""
        pass