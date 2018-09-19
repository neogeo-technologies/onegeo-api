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


from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from functools import reduce
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import HttpResponseSeeOther
from urllib.parse import urljoin


APP = 'onegeo_api'
API_BASE_PATH = settings.API_BASE_PATH


@method_decorator(csrf_exempt, name='dispatch')
class LoggedTasks(View):

    @BasicAuth()
    def get(self, request):
        defaults = {'user': request.user}
        tasks = Task.list_renderer(
            defaults,
            page_number=request.GET.get('page_number', 1),
            page_size=request.GET.get('page_size', 10))

        return JsonResponse(tasks, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class LoggedTask(View):

    @BasicAuth()
    def get(self, request, uuid):
        try:
            instance = Task.logged.get(uuid__startswith=uuid)
        except Task.DoesNotExist:
            raise Http404()
        if instance.user and instance.user != request.user:
            raise PermissionDenied()
        return JsonResponse(instance.detail_renderer())


@method_decorator(csrf_exempt, name='dispatch')
class AsyncTask(View):

    @BasicAuth()
    def get(self, request, uuid):

        try:
            instance = Task.asynchronous.get(uuid__startswith=uuid)
        except Task.DoesNotExist:
            raise Http404()
        if instance.user and instance.user != request.user:
            raise PermissionDenied()
        if instance.success is False:
            return HttpResponseSeeOther(
                redirect_to=reduce(
                    urljoin, ['/', API_BASE_PATH, instance.location[1:]]))
        if instance.success is True:
            return HttpResponseSeeOther(
                redirect_to=reduce(
                    urljoin, ['/', API_BASE_PATH, instance.target.location[1:]]))
        # else: instance.success is None
        return JsonResponse(data={
            # TODO task should be cancelable
            'status': 'pending',
            'start': instance.start_date,
            'elapsed_time': float('{0:.2f}'.format(
                instance.elapsed_time.total_seconds()))})
