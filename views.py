from ast import literal_eval
from re import search

from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from .models import Source, Resource, Context, Filter, Analyzer, Tokenizer
from django.conf import settings
from django.db import transaction, IntegrityError

from onegeo_manager.source import PdfSource
from onegeo_manager.index import Index
from onegeo_manager.context import PdfContext

import json

from . import utils

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR

@method_decorator(csrf_exempt, name="dispatch")
class SourceView(View):

    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_sources(user()), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
        return JsonResponse(utils.get_sources_id(user(), src_id), safe=False)

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
        return JsonResponse(utils.get_resources(user(), src_id), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ResourceIDView(View):

    def get(self, request, src_id, rsrc_id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_resources_id(user(), src_id, rsrc_id), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ContextView(View):


    def get(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        return JsonResponse(utils.get_contexts(user()), safe=False)


    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
            # if request.content_type != "application/json":
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

        try:
            context = Context.objects.get(resource=set_rscr)
            created = False
        except Context.DoesNotExist:
            created = True
            context = Context.objects.create(resource=set_rscr,
                                             name=name,
                                             clmn_properties=column_ppt,
                                             reindex_frequency=reindex_frequency)
        finally:
            status = created and 201 or 409
            response = HttpResponse()
            response.status_code = status
            if created:
                response['Location'] = '{}{}'.format(request.build_absolute_uri(), context.resource_id)
            return response


@method_decorator(csrf_exempt, name="dispatch")
class ContextIDView(View):

    def get(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        ctx_id = literal_eval(id)
        return JsonResponse(utils.get_context_id(user(), ctx_id), safe=False)

    def put(self, request, id):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        # if request.content_type != "application/json":
        if "application/json" not in request.content_type:
            return JsonResponse([{"Error": "Content-type incorrect"}], safe=False)
        data = request.body.decode('utf-8')
        body_data = json.loads(data)
        name = body_data['name']
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
            context.update(resource=set_rscr, name=name, clmn_properties=column_ppt)
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
        return JsonResponse(utils.get_filters(user()), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
        flt_name = (name.endswith('/') and name[:-1] or name)
        return JsonResponse(utils.get_filter_id(user(), flt_name), safe=False)

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
            filter.delete()
            response.status_code = 200
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
        return JsonResponse(utils.get_analyzers(user()), safe=False)

    @transaction.atomic
    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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

        return JsonResponse(utils.get_analyzers_id(user(), name), safe=False)

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
                return HttpResponseBadRequest()

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
                analyzer.filter.set(filters)
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

        return JsonResponse(utils.get_token(user()), safe=False)

    def post(self, request):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
        return JsonResponse(utils.get_token_id(user(), name), safe=False)

    def put(self, request, name):
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user

        if "application/json" not in request.content_type:
        # if request.content_type != "application/json":
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
            token.delete()
            response.status_code = 200
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