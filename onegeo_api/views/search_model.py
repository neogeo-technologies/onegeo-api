# Copyright (c) 2017-2019 Neogeo-Technologies.
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


from base64 import b64decode
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from importlib import import_module
import json
from onegeo_api.elastic import elastic_conn
from onegeo_api.exceptions import ElasticError
from onegeo_api.models import IndexProfile
from onegeo_api.models import SearchModel
from onegeo_api.utils import BasicAuth
import re
from requests.exceptions import HTTPError


@method_decorator(csrf_exempt, name='dispatch')
class SearchModelsList(View):

    @BasicAuth()
    def get(self, request):
        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True,
            'request': request}  # Ugly

        return JsonResponse(
            data=SearchModel.list_renderer(request.user, **opts), safe=False)

    @BasicAuth()
    def post(self, request):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse(
                data={'error': 'Malformed JSON', 'details': e.__str__()},
                status=400)

        data['user'] = request.user
        indexes = data.pop('indexes')

        # TODO Peut être remplacé par TypeError plus bas
        if 'title' not in data:
            msg = 'Some of the input paramaters needed are missing.'
            return JsonResponse(data={'error': msg}, status=400)

        try:
            instance = SearchModel.objects.create(**data)
        except TypeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except ValidationError as e:
            return JsonResponse(data={'error': e.message}, status=400)
        except AttributeError as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)
        except IntegrityError as e:
            return JsonResponse(data={'error': e.__str__()}, status=409)

        for item in indexes:
            try:
                val = re.search('indexes/(\w+)/?$', item).group(1)
            except AttributeError as e:
                return JsonResponse(data={'error': e.__str__()}, status=400)
            instance.indexes.add(
                IndexProfile.get_or_raise(val, user=data['user']))

        response = HttpResponse(status=201)
        response['Content-Location'] = instance.location
        return response


@method_decorator(csrf_exempt, name='dispatch')
class SearchModelsDetail(View):

    @BasicAuth()
    def get(self, request, name):

        opts = {
            'include': request.GET.get('include') == 'true' and True,
            'cascading': request.GET.get('cascading') == 'true' and True}

        search_model = SearchModel.get_or_raise(name, user=request.user)
        return JsonResponse(
            data=search_model.detail_renderer(**opts), status=200)

    @BasicAuth()
    def put(self, request, name):

        user = request.user

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse(
                data={'error': 'Malformed JSON', 'details': e.__str__()},
                status=400)

        expected = set(data.keys())
        fields = set(SearchModel.Extras.fields)
        if expected.intersection(fields) != fields:
            msg = 'Some of the input paramaters needed are missing: {}.'.format(
                ', '.join("'{}'".format(str(item)) for item in fields.difference(expected)))
            return JsonResponse(data={'error': msg}, status=400)

        data = dict((k, v) for k, v in data.items() if k in fields)

        instance = SearchModel.get_or_raise(name, user=user)

        try:
            data['indexes'] = [
                IndexProfile.get_or_raise(
                    re.search(
                        'indexes/(?P<name>(\w|-){1,100})/?$',
                        index_location).group('name'),
                    user=user)
                for index_location in data['indexes']]
        except Exception as e:
            return JsonResponse(data={'error': e.__str__()}, status=400)

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

    @BasicAuth()
    def delete(self, request, name):
        search_model = SearchModel.get_or_raise(name, user=request.user)
        search_model.delete()
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name='dispatch')
class Search(View):

    def get(self, request, name):

        user = None
        password = None
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == 'basic':
                user, password = b64decode(auth[1]).decode('utf-8').split(':')

        if name == '_all':
            index_profiles = [
                m.indexprofile for m in
                SearchModel.indexes.through.objects.filter(
                    searchmodel__in=SearchModel.objects.all())]
        else:
            try:
                instance = SearchModel.get_or_raise(name)
            except SearchModel.DoesNotExist:
                return HttpResponse(status=404)
            index_profiles = [
                m.indexprofile for m in
                SearchModel.indexes.through.objects.filter(searchmodel=instance)]

        index = [m.uuid for m in index_profiles]

        params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())
        if '_through' in params and not re.match(
                '^(false|no)$', params.pop('_through'), flags=re.IGNORECASE):
            try:
                return JsonResponse(
                    data=elastic_conn.search(index=index, params=params),
                    status=200)
            except ElasticError as e:
                return JsonResponse(
                    data={'error': e.__str__(), 'details': e.details},
                    status=e.status_code)

        # else:
        try:
            ext = import_module('...extensions.{}'.format(name), __name__)
        except ImportError:
            ext = import_module('...extensions.__init__', __name__)
        # else:
        try:
            plugin = ext.plugin(instance.query_dsl, index_profiles,
                                user=user, password=password)
        except HTTPError as err:
            return JsonResponse(
                data={'error': str(err)}, status=err.response.status_code)

        try:
            return plugin.output(
                elastic_conn.search(index=index, body=plugin.input(**params)))
        except ElasticError as e:
            return JsonResponse(
                data={'error': e.__str__(), 'details': e.details},
                status=e.status_code)

    def post(self, request, name):

        try:
            body = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse(
                data={'error': 'Malformed JSON', 'details': e.__str__()},
                status=400)

        user = None
        password = None
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == 'basic':
                user, password = b64decode(auth[1]).decode('utf-8').split(':')

        if name == '_all':
            index_profiles = [
                m.indexprofile for m in
                SearchModel.indexes.through.objects.filter(
                    searchmodel__in=SearchModel.objects.all())]
        else:
            try:
                instance = SearchModel.get_or_raise(name)
            except SearchModel.DoesNotExist:
                return HttpResponse(status=404)
            index_profiles = [
                m.indexprofile for m in
                SearchModel.indexes.through.objects.filter(searchmodel=instance)]

        index = [m.uuid for m in index_profiles]

        params = dict((k, ','.join(v)) for k, v in dict(request.GET).items())

        if '_through' in params and not re.match(
                '^(false|no)$', params.pop('_through'), flags=re.IGNORECASE):
            try:
                return JsonResponse(
                    data=elastic_conn.search(
                        index=index, params=params, body=body),
                    status=200)
            except ElasticError as e:
                return JsonResponse(
                    data={'error': e.__str__(), 'details': e.details},
                    status=e.status_code)
        # else:
        return HttpResponse(status=400)
