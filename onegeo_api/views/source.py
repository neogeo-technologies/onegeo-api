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
from onegeo_api.models import CeleryTask
from django.contrib.auth.models import User
from onegeo_api.tasks import create_resources_with_log
import sys, os, django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.conf import settings

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
        task_url = settings.CELERY_TASK_URL+ "api/tasks/"+instance.alias.handle + str(instance.pk)

        return JsonResponse(status=202, data={'task_url':task_url})


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
    def delete(self, request, alias):
        source = Source.get_or_raise(slash_remove(alias), request.user)
        source.delete()
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class Status(View):

    def get(self, request,id=None):

        if id:
            task = list(CeleryTask.objects.filter(task_id=id).values('task_id',
            'status','user__username','header_location'))


        # if request.user:
        #     try:
        #         current_user = User.objects.get(username=request.user.username)
        #
        #         for elt in CeleryTask.objects.filter(user=current_user):
        #             elt.save()
        #             res.append({'taskid':elt.celery_task_id,'status':elt.status,'header_location':elt.header_location})
        #     except:
        #         pass
        if task:
            return JsonResponse(task, safe=False)
        else:
            return JsonResponse("task not found, please retry in few minutes", safe=False)
