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
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
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
    def put(self, request, nickname):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        user = request.user
        index_profile = IndexProfile.get_or_raise(nickname, user)

        expected = set(data.keys())
        fields = set(IndexProfile.Extras.fields)
        if expected.intersection(fields) != fields:
            msg = 'Some of the input paramaters needed are missing: {}.'.format(
                ', '.join("'{}'".format(str(item)) for item in fields.difference(expected)))
            return JsonResponse({'error': msg}, status=400)

        data = dict((k, v) for k, v in data.items() if k in fields)

        if data['resource'] != index_profile.resource.location:
            msg = 'The resource could not be changed'
            return JsonResponse({'error': msg}, status=400)
        # else:
        data['resource'] = index_profile.resource
        try:
            for k, v in data.items():
                setattr(index_profile, k, v)
            index_profile.save()
        except IntegrityError as e:
            return JsonResponse({'error': e.__str__()}, status=409)
        except ValidationError as e:
            return JsonResponse({'error': e.__str__()}, status=400)
        # other exceptions -> 500
        return HttpResponse(status=204)

    @BasicAuth()
    def delete(self, request, nickname):

        index_profile = \
            IndexProfile.get_or_raise(nickname, request.user)
        index_profile.delete()

        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksList(View):

    @BasicAuth()
    def get(self, request, nickname):
        index_profile = IndexProfile.get_or_raise(nickname, request.user)
        defaults = {'alias': index_profile.alias, 'user': request.user}
        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesTasksDetail(View):

    @BasicAuth()
    def get(self, request, nickname, tsk_id):
        index_profile = IndexProfile.get_or_raise(nickname, request.user)
        task = Task.get_with_permission(
            {'id': literal_eval(tsk_id), 'alias': index_profile.alias},
            request.user)
        return JsonResponse(task.detail_renderer(), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesPublish(View):

    @BasicAuth()
    def get(self, request, nickname):

        index_profile = IndexProfile.get_or_raise(nickname, request.user)

        related_tasks = Task.objects.filter(
            user=request.user, alias=index_profile.alias,
            success__isnull=True, stop_date__isnull=True, description=2)

        if len(related_tasks) > 0:
            return JsonResponse(
                data={
                    'error': 'You cannot overload a task that is currently running.',
                    'details': {
                        'current_task': [m.detail_renderer() for m in related_tasks]}},
                status=423)

        task = Task.objects.create(
            user=request.user, alias=index_profile.alias, description='2')
        create_es_index.apply_async(
            kwargs={'nickname': nickname, 'user': request.user.pk},
            task_id=str(task.celery_id))

        return HttpResponse(status=202)
