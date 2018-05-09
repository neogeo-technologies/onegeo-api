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


from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
# from functools import reduce
from onegeo_api.models import Analysis
# import operator


@method_decorator(csrf_exempt, name='dispatch')
class AnalyzerList(View):

    def get(self, request):
        # data = reduce(operator.add, [
        #     item.get_analyzers() for item
        #     in Analysis.objects.filter(user=request.user)])
        data = [item.get_analyzer() for item
                in Analysis.objects.filter(user=request.user)]
        return JsonResponse(data=data, safe=False)
