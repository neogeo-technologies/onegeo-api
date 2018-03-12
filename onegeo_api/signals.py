from django.apps import apps
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from onegeo_api.models import Analyzer
from onegeo_api.models import Filter
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source
from onegeo_api.models import Tokenizer
from onegeo_api.tasks import create_resources_with_log
from celery.result import AsyncResult
from onegeo_api.models import Dashboard

# Ces connecteurs de signaux ont été enregistré dans les modules apps.py et __init__.py de l'application


@receiver(post_save, sender=Source)
def on_post_save_source(sender, instance, *args, **kwargs):

    task_id = instance.alias.handle + str(instance.pk)
    data = {'protocol': instance.protocol,
    'name': instance.name,
    'user': instance.user.pk,
    'uri': instance.uri}
    # traitement de la requete par Celery
    # task = create_resources_with_log.delay(data)
    task = create_resources_with_log.apply_async(kwargs=data, task_id=task_id)



@receiver(post_delete, sender=Analyzer)
@receiver(post_delete, sender=Filter)
@receiver(post_delete, sender=SearchModel)
@receiver(post_delete, sender=Tokenizer)
@receiver(post_delete, sender=Source)
@receiver(post_delete, sender=Resource)
@receiver(post_delete, sender=IndexProfile)
def delete_related_alias(sender, instance, **kwargs):
    if instance.alias:
        instance.alias.delete()
