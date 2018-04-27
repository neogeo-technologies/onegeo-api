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
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth


@method_decorator(csrf_exempt, name='dispatch')
class TasksList(View):

    @BasicAuth()
    def get(self, request):
        defaults = {'user': request.user}
        return JsonResponse(Task.list_renderer(defaults), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class TasksDetail(View):

    @BasicAuth()
    def get(self, request, id):
        task = Task.get_with_permission({'id': literal_eval(id)}, request.user)
        if task.success:
            return HttpResponseRedirect(task['header_location'])  # TODO 303
        return JsonResponse(task.detail_renderer, safe=False)
