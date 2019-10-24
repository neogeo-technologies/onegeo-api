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


from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Source
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import subdirectories


@method_decorator(csrf_exempt, name='dispatch')
class Uris(View):

    @BasicAuth()
    def get(self, request):
        try:
            return JsonResponse(
                data=subdirectories(settings.SOURCE_ROOT_DIR), safe=False)
        except:
            return []


@method_decorator(csrf_exempt, name='dispatch')
class Protocols(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(data=dict(Source.PROTOCOL_CHOICES), safe=False)
