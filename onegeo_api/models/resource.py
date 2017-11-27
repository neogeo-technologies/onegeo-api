from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.db import models
import uuid

from onegeo_api.utils import clean_my_obj


class Resource(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__rsrc = None

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250)
    columns = JSONField("Columns")

    # FK & alt
    source = models.ForeignKey("onegeo_api.Source", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Resource"

    @property
    def rsrc(self):
        return self.__rsrc

    def set_rsrc(self, rsrc):
        self.__rsrc = rsrc

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @property
    def format_data(self):
        Context = apps.get_model(app_label='onegeo_api', model_name='Context')
        d = {"id": self.short_uuid,
             "location": "/sources/{}/resources/{}".format(self.source.short_uuid, self.short_uuid),
             "name": self.name,
             "columns": self.columns}
        try:
            contexts = Context.objects.filter(resources=self)
        except Context.DoesNotExist:
            pass
        else:
            d.update(index=[ctx.format_data["location"] for ctx in contexts])
        finally:
            return clean_my_obj(d)

    @classmethod
    def get_from_uuid(cls, src_uuid, rsrc_uuid, user=None):
        Source = apps.get_model(app_label='onegeo_api', model_name='Source')
        src = Source.get_from_uuid(uuid=src_uuid)
        if src:
            if user:
                resources = cls.objects.filter(source__user=user)
            else:
                resources = cls.objects.filter(source=src)
            for rsrc in resources:
                if str(rsrc.uuid)[:len(rsrc_uuid)] == rsrc_uuid:
                    return rsrc
        return None

    @classmethod
    def format_by_filter(cls, src_uuid, user):
        Source = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = Source.get_from_uuid(uuid=src_uuid, user=user)
        rsrc = cls.objects.filter(source=source, source__user=user).order_by("name")
        return [r.format_data for r in rsrc]
