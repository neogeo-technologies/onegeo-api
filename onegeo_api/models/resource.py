from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.http import Http404
from django.db import models
from django.core.exceptions import PermissionDenied

from onegeo_api.utils import clean_my_obj
from onegeo_api.models.abstracts import AbstractModelProfile


class Resource(AbstractModelProfile):

    columns = JSONField("Columns")

    # FK & alt
    source = models.ForeignKey("onegeo_api.Source", on_delete=models.CASCADE)
    context = models.ForeignKey("onegeo_api.Context", null=True, blank=True)

    class Meta:
        verbose_name = "Resource"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__rsrc = None

    def save(self, *args, **kwargs):
        kwargs['model_name'] = 'Resource'
        return super().save(*args, **kwargs)

    @property
    def rsrc(self):
        return self.__rsrc

    def set_rsrc(self, rsrc):
        self.__rsrc = rsrc

    @property
    def detail_renderer(self):
        d = {"location": "/sources/{}/resources/{}".format(self.source.alias.handle, self.alias.handle),
             "name": self.name,
             "alias": self.alias.handle,
             "index": self.context.detail_renderer.get("location", "") if self.context else "",
             "columns": self.columns}

        return clean_my_obj(d)

    @classmethod
    def list_renderer(cls, src_alias, user):
        Source = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = Source.get_with_permission(src_alias, user)
        instances = cls.objects.filter(source=source).order_by("name")
        return [resource.detail_renderer for resource in instances]

    @classmethod
    def custom_create(cls, source, name, columns, user, alias):
        Alias = apps.get_model(app_label='onegeo_api', model_name='Alias')
        alias = Alias.custom_create(model_name="Resource", handle=alias)
        resource = cls.objects.create(
            source=source, name=name,
            columns=columns, user=user, alias=alias)
        return resource

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucune ressource ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette ressource")
        return instance
