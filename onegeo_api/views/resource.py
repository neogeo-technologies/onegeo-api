from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
from onegeo_api.utils import BasicAuth


@method_decorator(csrf_exempt, name='dispatch')
class ResourcesList(View):

    @BasicAuth()
    def get(self, request, nickname):
        user = request.user
        source = Source.get_or_raise(nickname, user)

        try:
            task = Task.objects.get(alias=source.alias)
        except Task.DoesNotExist:
            data = Resource.list_renderer(nickname, user)
            opts = {'safe': False}
        # else:
        if task.stop_date and task.success is True:
            data = Resource.list_renderer(nickname, user)
            opts = {'safe': False}

        if task.stop_date and task.success is False:
            # TODO
            data = {'error': 'Connection to the data source failed.'}
            opts = {'status': 424}

        if not task.stop_date and not task.success:
            data = {'error': (
                'Connection to the data source is running to analyzing. '
                'Please wait for a moment then try again.')}
            opts = {'status': 423}

        return JsonResponse(data=data, **opts)


@method_decorator(csrf_exempt, name='dispatch')
class ResourcesDetail(View):

    @BasicAuth()
    def get(self, request, nickname):
        resource = Resource.get_or_raise(nickname, request.user)
        return JsonResponse(resource.detail_renderer())
