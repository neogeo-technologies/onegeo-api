from __future__ import absolute_import, unicode_literals
import random
from celery.decorators import task
from django.contrib.auth.models import User
from onegeo_api.models import Source
from django.apps import apps
from onegeo_api.models import Alias,CeleryTask
from django.utils import timezone
from celery import uuid

@task(name="create_resources_with_log",ignore_result=False)
def create_resources_with_log(**kwargs):

   Task = apps.get_model(app_label='onegeo_api', model_name='Task')
   Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
   alias = Alias.objects.create(model_name=kwargs['name'])
   user = User.objects.get(pk=kwargs['user'])
   instance = Source.objects.get(protocol=kwargs['protocol'],
   name=kwargs['name'], user = user, uri=kwargs['uri'])
   description = "Création des ressources en cours. "

   tsk = Task.objects.create(user=user, alias=alias, description=description)
   # save info about Celery Task
   celery_task,_created = CeleryTask.objects.get_or_create(task_id=create_resources_with_log.request.id,
   user=user)
   celery_task.status = "IN PROGRESS"
   celery_task.save()

   try:

      for item in instance.onegeo.get_resources():
         Resource.objects.create(**{
           'source': instance, 'name': item.name,
           'columns': item.columns, 'user': user})

      tsk.success = True
      tsk.description = "Les ressources ont été créées avec succès. "
      print(tsk.description)
   except Exception as err:
       print(err)
       celery_task.status = "FAILED"
       celery_task.save()
       tsk.success = False
       tsk.description = str(err)[255:]  # TODO
   finally:
       print("task done" ,instance.location )
       celery_task.status = "SUCCESS"
       celery_task.header_location = instance.location
       celery_task.save()
       tsk.stop_date = timezone.now()
       tsk.save()
