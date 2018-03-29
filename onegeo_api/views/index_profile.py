from ast import literal_eval
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json
from onegeo_api.celery_tasks import create_es_index
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.exceptions import ExceptionsHandler
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import errors_on_call
import re


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesList(View):

    @BasicAuth()
    def get(self, request):
        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True}

        return JsonResponse(
            IndexProfile.list_renderer(request.user, **opts), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    # @ExceptionsHandler(actions=errors_on_call())
    def post(self, request):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        data['user'] = request.user

        if 'name' not in data or 'resource' not in data:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse({'error': msg}, status=400)

        try:
            resource_nickname = re.search(
                '^/sources/(\w+)/resources/(\w+)/?$',
                data.pop('resource')).group(2)
        except AttributeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        data['resource'] = \
            Resource.get_or_raise(resource_nickname, data['user'])

        try:
            instance = IndexProfile.objects.create(**data)
        except ValidationError as e:
            return JsonResponse({'error': e.__str__()}, status=400)
        except IntegrityError as e:
            return JsonResponse({'error': e.__str__()}, status=409)

        response = HttpResponse(status=201)
        response['Content-Location'] = instance.location
        return response


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesDetail(View):

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):

        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True}
        index_profile = IndexProfile.get_or_raise(nickname, request.user)

        return JsonResponse(
            index_profile.detail_renderer(**opts),
            safe=False, status=200)

    @BasicAuth()
    @ContentTypeLookUp()
    # @ExceptionsHandler(actions=errors_on_call())
    def put(self, request, nickname):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        # Check linked resource
        try:
            resource_nickname = re.search(
                    '^/sources/(\w+)/resources/(\w+)/?$',
                    data.pop('resource_location')).group(2)
            # resource_nickname = re.search(
            #     '^/sources/(\w+)/resources/(\w+)/?$',
            #     data.pop('resource')).group(2)
        except AttributeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        user = request.user
        data['resource'] = Resource.get_or_raise(resource_nickname, user)
        index_profile = IndexProfile.get_or_raise(nickname, user)

        fields = set(IndexProfile.Extras.fields)
        if set(data.keys()).intersection(fields) != fields:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse({'error': msg}, status=400)
        # else:
        data = dict((k, v) for k, v in data.items() if k in fields)

        if index_profile.resource.alias.handle != resource_nickname:
            # TODO Gestion des erreurs
            return JsonResponse({'error': 'TODO'}, status=400)
        for k, v in data.items():
            setattr(index_profile, k, v)

        try:
            index_profile.save()
        except IntegrityError as e:
            return JsonResponse({'error': e.__str__()}, status=409)
        except ValidationError as e:
            return JsonResponse({'error': e.__str__()}, status=400)
        # other exceptions -> 500
        return HttpResponse(status=204)

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def delete(self, request, nickname):
        index_profile = \
            IndexProfile.get_or_raise(nickname, request.user)
        # IndexProfile.get_with_permission(slash_remove(alias), request.user)
        # Erreur sur IndexProfile.delete() suite a erreur sur ES_wrapper
        # "elastic_conn.delete_index_by_alias" doit etre réintégrer
        index_profile.delete()
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksList(View):

    # @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):
        index_profile = IndexProfile.get_or_raise(nickname, request.user)
        defaults = {"alias": index_profile.alias, "user": request.user}
        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksDetail(View):

    # @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname, tsk_id):
        index_profile = IndexProfile.get_or_raise(nickname, request.user)
        task = Task.get_with_permission(
            {"id": literal_eval(tsk_id), "alias": index_profile.alias},
            request.user)
        return JsonResponse(task.detail_renderer(), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesPublish(View):

    @BasicAuth()
    def get(self, request, nickname):

        index_profile = IndexProfile.get_or_raise(nickname, request.user)
        # possibilté d'avoir plusisuer profile pour une seule source
        task = Task.objects.create(user=request.user,
                                   alias=index_profile.alias,
                                   name=index_profile.name,
                                   description="2")

        create_es_index.apply_async(
            kwargs={'nickname': nickname, 'user': request.user.pk},
            task_id=str(task.celery_id))

        return HttpResponse(status=202)
