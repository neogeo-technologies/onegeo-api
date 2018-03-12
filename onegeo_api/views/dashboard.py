from django.http import JsonResponse
from django.views.generic import View
from onegeo_api.utils import BasicAuth
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from onegeo_api.models import Dashboard

@method_decorator(csrf_exempt, name="dispatch")
class DashboardList(View):

    @BasicAuth()
    def get(self, request):
        opts = {'include': request.GET.get('include') == 'true' and True}
        return JsonResponse(
            Dashboard.list_renderer(request.user, **opts), safe=False)
