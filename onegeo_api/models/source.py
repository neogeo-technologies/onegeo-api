from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from onegeo_api.models.abstracts import AbstractModelProfile
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

    @property
    def onegeo(self):
        return onegeo_manager.Source(self.uri, self.protocol)

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

        return super().save(*args, **kwargs)
