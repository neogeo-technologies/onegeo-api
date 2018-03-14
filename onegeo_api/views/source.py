from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import json
from onegeo_api.exceptions import ContentTypeLookUp
from onegeo_api.models import Source
from onegeo_api.utils import BasicAuth
from onegeo_api.utils import slash_remove
from onegeo_api.models import Dashboard


@method_decorator(csrf_exempt, name="dispatch")
class SourcesList(View):

    @BasicAuth()
    def get(self, request):
        opts = {'include': request.GET.get('include') == 'true' and True}
        return JsonResponse(
            Source.list_renderer(request.user, **opts), safe=False)

    @BasicAuth()
    @ContentTypeLookUp()
    # @ExceptionsHandler(actions=errors_on_call())
    def post(self, request):

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            return JsonResponse({'error': str(e)}, status=400)

        data['user'] = request.user
        try:
            instance = Source.objects.create(**data)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except IntegrityError as e:
            return JsonResponse({'error': str(e)}, status=409)

        # The request has been accepted for processing
        # but the processing has not been completed
        task_id = instance.alias.handle + str(instance.pk)
        task_url = "/tasks/" + instance.alias.handle + str(instance.pk)
        # save info about Celery Task
        celery_task, _created = Dashboard.objects.get_or_create(
            task_id=task_id,
            user=request.user,
            status="IN PROGRESS")

        return JsonResponse(data={'task_url': task_url}, status=202)


@method_decorator(csrf_exempt, name="dispatch")
class SourcesDetail(View):

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def get(self, request, nickname):

        opts = {'include': request.GET.get('include') == 'true' and True}
        # Pas logique (TODO)
        instance = Source.get_or_raise(slash_remove(nickname), request.user)
        return JsonResponse(instance.detail_renderer(**opts), safe=False)

    @BasicAuth()
    # @ExceptionsHandler(actions=errors_on_call())
    def delete(self, request, nickname):

        source = Source.get_or_raise(slash_remove(nickname), request.user)
        source.delete()
        return HttpResponse(status=204)
