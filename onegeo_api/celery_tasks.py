from __future__ import absolute_import
from __future__ import unicode_literals
from celery.decorators import task
from celery.utils.log import get_task_logger
from django.apps import apps
from django.utils import timezone


logger = get_task_logger(__name__)


@task(name="create_resources_with_log", ignore_result=False)
def create_resources_with_log(**kwargs):

    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Source = apps.get_model(app_label='onegeo_api', model_name='Source')
    Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')

    source = Source.objects.get(pk=kwargs['pk'])
    task = Task.objects.get(celery_id=create_resources_with_log.request.id)

    try:
        for item in source.onegeo.get_resources():
            Resource.objects.create(**{
                'source': source, 'name': item.name,
                'columns': item.columns, 'user': source.user})
    except Exception as e:
        logger.error(e)
        task.success = False
    else:
        task.success = True
    finally:
        task.stop_date = timezone.now()
        task.save()
