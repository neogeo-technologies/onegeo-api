from django.db.models.signals import post_delete
from django.dispatch import receiver
from onegeo_api.models import Analyzer
from onegeo_api.models import Filter
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source
from onegeo_api.models import Tokenizer


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
