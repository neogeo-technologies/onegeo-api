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
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Source
from onegeo_api.utils import BasicAuth
from pathlib import Path


PDF_DIR_PATH = settings.PDF_DATA_BASE_DIR


@method_decorator(csrf_exempt, name='dispatch')
class Uris(View):

    # TODO not only for pdf dir..

    def all_sub_directories(self, dirpath=PDF_DIR_PATH):
        p = Path(dirpath)
        if not p.exists():
            raise ConnectionError('Given path does not exist.')
        # else:
        return ['file:///{}'.format(x.name) for x in p.iterdir() if x.is_dir()]

    @BasicAuth()
    def get(self, request):
        return JsonResponse(
            data='pdf' in dict(Source.PROTOCOL_CHOICES) and self.all_sub_directories() or [],
            safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class Protocols(View):

    @BasicAuth()
    def get(self, request):
        return JsonResponse(data=dict(Source.PROTOCOL_CHOICES), safe=False)
