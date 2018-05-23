# Copyright (c) 2017-2018 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from ast import literal_eval
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json
from onegeo_api.celery_tasks import indexing
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
import re
from uuid import uuid4


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
    def post(self, request):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        data['user'] = request.user

        # TODO Peut être remplacé par TypeError plus bas
        if 'title' not in data or 'resource' not in data:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse({'error': msg}, status=400)

        try:
            resource_nickname = re.search(
                '^/sources/(\w+)/resources/(\w+)/?$',
                data.pop('resource')).group(2)
        except AttributeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        data['resource'] = \
            Resource.get_or_raise(resource_nickname, user=data['user'])

        try:
            instance = IndexProfile.objects.create(**data)
        except TypeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except ValidationError as e:
            return JsonResponse(data={'error': e.message}, status=400)
        except AttributeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except IntegrityError as e:
            return JsonResponse(data={'error': e.__str__()}, status=409)

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
        index_profile = IndexProfile.get_or_raise(nickname, user=request.user)

        return JsonResponse(
            index_profile.detail_renderer(**opts),
            safe=False, status=200)

    @BasicAuth()
    def put(self, request, nickname):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        user = request.user
        index_profile = IndexProfile.get_or_raise(nickname, user=user)

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
        except TypeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except ValidationError as e:
            return JsonResponse(data={'error': e.message}, status=400)
        except AttributeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except IntegrityError as e:
            return JsonResponse(data={'error': e.__str__()}, status=409)

        return HttpResponse(status=204)

    @BasicAuth()
    def delete(self, request, nickname):

        index_profile = \
            IndexProfile.get_or_raise(nickname, user=request.user)
        index_profile.delete()

        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class IndexProfilesTasksList(View):

    @BasicAuth()
    def get(self, request, nickname):
        index_profile = IndexProfile.get_or_raise(nickname, user=request.user)
        defaults = {'alias': index_profile.alias, 'user': request.user}
        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesTasksDetail(View):

    @BasicAuth()
    def get(self, request, nickname, tsk_id):
        index_profile = IndexProfile.get_or_raise(nickname, user=request.user)
        task = Task.get_with_permission(
            {'id': literal_eval(tsk_id), 'alias': index_profile.alias},
            request.user)
        return JsonResponse(task.detail_renderer(), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class IndexProfilesIndexing(View):

    @BasicAuth()
    def get(self, request, nickname):
        index_profile = IndexProfile.get_or_raise(nickname, user=request.user)

        indexing.apply_async(
            kwargs={'alias': index_profile.alias.pk,
                    'index_profile': index_profile.pk,
                    'user': request.user.pk},
            task_id=str(uuid4()))

        return HttpResponse(status=202)
