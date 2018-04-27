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
from onegeo_api.models import Source
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import slash_remove


@method_decorator(csrf_exempt, name="dispatch")
class SourcesList(View):

    @BasicAuth()
    def get(self, request):
        opts = {'include': request.GET.get('include') == 'true' and True}
        return JsonResponse(
            Source.list_renderer(request.user, **opts), safe=False)

    @BasicAuth()
    def post(self, request):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        data['user'] = request.user
        try:
            Source.objects.create(**data)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except IntegrityError as e:
            return JsonResponse({'error': str(e)}, status=409)

        return JsonResponse(data={}, status=202)


@method_decorator(csrf_exempt, name="dispatch")
class SourcesDetail(View):

    @BasicAuth()
    def get(self, request, nickname):

        opts = {'include': request.GET.get('include') == 'true' and True}
        # Pas logique (TODO)
        instance = Source.get_or_raise(nickname, request.user)
        return JsonResponse(instance.detail_renderer(**opts), safe=False)

    @BasicAuth()
    def put(self, request, nickname):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        expected = set(data.keys())
        fields = set(Source.Extras.fields)
        if expected.intersection(fields) != fields:
            msg = 'Some of the input paramaters needed are missing: {}.'.format(
                ', '.join("'{}'".format(str(item)) for item in fields.difference(expected)))
            return JsonResponse({'error': msg}, status=400)

        instance = Source.get_or_raise(nickname, request.user)

        try:
            for k, v in data.items():
                setattr(instance, k, v)
            instance.save()
        except IntegrityError as e:
            return JsonResponse({'error': e.__str__()}, status=409)
        except ValidationError as e:
            return JsonResponse({'error': e.__str__()}, status=400)
        # other exceptions -> 500
        return HttpResponse(status=204)

    @BasicAuth()
    def delete(self, request, nickname):

        source = Source.get_or_raise(slash_remove(nickname), request.user)
        source.delete()
        return HttpResponse(status=204)
