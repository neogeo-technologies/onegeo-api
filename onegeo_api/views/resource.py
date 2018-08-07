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


from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth


@method_decorator(csrf_exempt, name='dispatch')
class ResourcesList(View):

    @BasicAuth()
    def get(self, request, name):
        user = request.user
        source = Source.get_or_raise(name, user=user)

        try:
            task = Task.logged.get(alias=source.alias)
        except Task.DoesNotExist:
            data = {'error': ('Something wrong happened. '
                              'Database was corrupted '
                              'and the related task disappeared. '
                              'How could I solve that?')}
            opts = {'status': 418}
        else:
            if task.stop_date and task.success is True:
                data = Resource.list_renderer(name, user)
                opts = {'safe': False}

            if task.stop_date and task.success is False:
                data = {'error': 'Connection to the data source failed.'}
                opts = {'status': 424}

            if not task.stop_date and not task.success:
                data = {'error': (
                    'Connection to the data source is running to analyzing. '
                    'Please wait for a moment then try again.')}
                opts = {'status': 423}

        return JsonResponse(data=data, **opts)


@method_decorator(csrf_exempt, name='dispatch')
class ResourcesDetail(View):

    @BasicAuth()
    def get(self, request, source, name):
        resource = Resource.get_or_raise(name, user=request.user)
        return JsonResponse(resource.detail_renderer())

    @BasicAuth()
    def put(self, request, source, name):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': e.__str__()}, status=400)

        user = request.user
        instance = Resource.get_or_raise(name, user=user)

        expected = set(data.keys())
        fields = set(Resource.Extras.fields)
        if expected.intersection(fields) != fields:
            msg = 'Some of the input paramaters needed are missing: {}.'.format(
                ', '.join("'{}'".format(str(item)) for item in fields.difference(expected)))
            return JsonResponse({'error': msg}, status=400)

        data = dict((k, v) for k, v in data.items() if k in fields)
        try:
            for k, v in data.items():
                setattr(instance, k, v)
            instance.save()
        except TypeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except ValidationError as e:
            return JsonResponse(data={'error': e.message}, status=400)
        except AttributeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except IntegrityError as e:
            return JsonResponse(data={'error': e.__str__()}, status=409)

        return HttpResponse(status=204)
