from django.http import JsonResponse
from django.views.generic import View
from onegeo_api.utils import BasicAuth
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from onegeo_api.models import Dashboard
from django.http import HttpResponseRedirect


@method_decorator(csrf_exempt, name="dispatch")
class DashboardList(View):

    @BasicAuth()
    def get(self, request):

        opts = {'include': request.GET.get('include') == 'true' and True}
        return JsonResponse(
            Dashboard.list_renderer(request.user, **opts), safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class Status(View):

    def get(self, request, id=None):

        try:
            # id = "203c520333"
            task = Dashboard.objects.values(
                'task_id',
                'status',
                'user__username',
                'header_location').get(task_id=id)

            if task['status'] == "SUCCESS":
                return HttpResponseRedirect(task['header_location'])
                # return HttpResponseRedirect('/query?path='+task['header_location'])
            else:
                return JsonResponse(task, status=202)
        except Exception as e:
            return JsonResponse("task not found, please retry in few minutes", safe=False)
