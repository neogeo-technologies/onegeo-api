from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from onegeo_api.celery_tasks import create_resources_with_log
from onegeo_api.models.abstracts import AbstractModelProfile
from onegeo_api.models.task import Task
import onegeo_manager
import re


class Source(AbstractModelProfile):

    class Meta(object):
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'

    PROTOCOL_CHOICES = onegeo_manager.protocol.all()

    protocol = models.CharField(
        verbose_name='Protocol', max_length=250, choices=PROTOCOL_CHOICES)

    uri = models.CharField(verbose_name='URI', max_length=2048)

    @property
    def location(self):
        return '/sources/{}'.format(self.alias.handle)

    @location.setter
    def location(self):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self):
        return onegeo_manager.Source(self.uri, self.protocol)

    @onegeo.setter
    def onegeo(self):
        raise AttributeError('Attibute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def iter_resources(self):
        instance = apps.get_model(
            app_label='onegeo_api', model_name='Resource')
        return iter(item for item in instance.objects.filter(source=self))

    def detail_renderer(self, **kwargs):
        return {
            'location': self.location,
            'name': self.name,
            'protocol': self.protocol,
            'uri': self.uri}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [item.detail_renderer(**opts) for item
                in cls.objects.filter(user=user).order_by('name')]

    def save(self, *args, **kwargs):

        if not self.name or not self.protocol or not self.uri:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if not re.match('^[\w\s]+$', self.name):
            raise ValidationError("Malformed 'name' parameter.")

        if self.protocol not in dict(self.PROTOCOL_CHOICES).keys():
            raise ValidationError("'protocol' input parameters is unauthorized.")

        # TODO
        # if self.uri not... :
        #     pass

        super().save(*args, **kwargs)

        task = Task.objects.create(user=self.user, alias=self.alias)
        create_resources_with_log.apply_async(
            kwargs={'pk': self.pk}, task_id=str(task.celery_id))
