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


from django.http import Http404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Analysis
from onegeo_api.utils import BasicAuth


@method_decorator(csrf_exempt, name='dispatch')
class Analyses(View):

    @BasicAuth()
    def get(self, request, component=None, name=None):

        if component and name:
            try:
                data = Analysis.get_component_by_name(
                    component[:-1], name, user=request.user)
            except Analysis.DoesNotExist:
                raise Http404()
        else:
            data = Analysis.get_components(user=request.user)
            if component:
                if component not in data:
                    raise Http404()
                data = data[component]

        return JsonResponse(data=data, safe=False)
