from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from onegeo_api.utils import clean_my_obj
from onegeo_api.models import AbstractModelProfile


class Resource(AbstractModelProfile):

    columns = JSONField("Columns")

    # FK & alt
    source = models.ForeignKey("onegeo_api.Source", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Resource"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__rsrc = None

    @property
    def rsrc(self):
        return self.__rsrc

    def set_rsrc(self, rsrc):
        self.__rsrc = rsrc

    @property
    def detail_renderer(self):
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
    def list_renderer(cls, src_uuid, user):
        Source = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = Source.get_with_permission(src_uuid, user)
        instances = cls.objects.filter(source=source).order_by("name")
        return [resource.detail_renderer for resource in instances]

    @classmethod
    def create_with_response(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_from_uuid(cls, short_uuid):
        for obj in cls.objects.all():
            if str(obj.uuid)[:len(short_uuid)] == short_uuid:
                return obj
        raise Http404

    @classmethod
    def get_from_name(cls, name):
        return get_object_or_404(cls, name=name)

    @classmethod
    def get_with_permission(cls, short_uuid, user):
        instance = cls.get_from_uuid(short_uuid)
        if instance.source.user != user:
            raise PermissionDenied
        return instance

    # @classmethod
    # def format_by_filter(cls, src_uuid, user):
    #     Source = apps.get_model(app_label='onegeo_api', model_name='Source')
    #     source = Source.get_from_uuid(uuid=src_uuid, user=user)
    #     rsrc = cls.objects.filter(source=source, source__user=user).order_by("name")
    #     return [r.format_data for r in rsrc]

    # @classmethod
    # def custom_get_object_or_404(cls, src_uuid, rsrc_uuid):
    #     Source = apps.get_model(app_label='onegeo_api', model_name='Source')
    #     source = Source.custom_get_object_or_404(src_uuid)
    #     instances = cls.objects.filter(source=source)
    #     for obj in instances:
    #         if str(obj.uuid)[:len(rsrc_uuid)] == rsrc_uuid:
    #             return obj
    #     raise Http404
    #
    # @classmethod
    # def user_access(cls, src_uuid, rsrc_uuid, user):
    #     instance = cls.custom_get_object_or_404(src_uuid, rsrc_uuid)
    #     if instance.user != user:
    #         raise PermissionDenied
    #     return instance
    # @classmethod
    # def get_from_uuid(cls, src_uuid, rsrc_uuid, user=None):
    #     Source = apps.get_model(app_label='onegeo_api', model_name='Source')
    #     src = Source.get_from_uuid(uuid=src_uuid)
    #     if src:
    #         if user:
    #             resources = cls.objects.filter(source__user=user)
    #         else:
    #             resources = cls.objects.filter(source=src)
    #         for rsrc in resources:
    #             if str(rsrc.uuid)[:len(rsrc_uuid)] == rsrc_uuid:
    #                 return rsrc
    #     return None
