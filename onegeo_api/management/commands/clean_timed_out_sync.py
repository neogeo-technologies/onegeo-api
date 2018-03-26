from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from onegeo_api.models import Task
import re


NOW = timezone.now()


class Command(BaseCommand):

    help = 'Update indexes'

    def __init__(self, *args, **kwargs):

        self.conn = Elasticsearch([{'host': settings.ES_VAR['HOST']}])
        self.conn.cluster.health(wait_for_status='yellow', request_timeout=60)
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        for instance in Task.objects.all():
            if not instance.stop_date:
                delta = NOW - instance.start_date
                if (delta.days * 24 + delta.seconds // 3600) > 20:
                    res = re.search("\'(\w{7})\'", instance.description)
                    if res:
                        index = res.group(1)
                        try:
                            self.conn.indices.delete(index=index)
                        except NotFoundError:
                            pass
                    instance.success = False
                    instance.description = \
                        "Délai de synchronisation dépassé (Supprimé '{}').".format(index)
                    instance.stop_date = NOW
                    instance.save()
