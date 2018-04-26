from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from onegeo_api.models.abstracts import AbstractModelProfile
import onegeo_manager
import re


class Source(AbstractModelProfile):

    class Extras(object):
        fields = ('location', 'name', 'protocol', 'uri')

    class Meta(object):
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'

    PATHNAME = '/sources/{source}'

    PROTOCOL_CHOICES = onegeo_manager.protocol.all()

    protocol = models.CharField(
        verbose_name='Protocol', max_length=250, choices=PROTOCOL_CHOICES)

    uri = models.CharField(verbose_name='URI', max_length=2048)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None

    @property
    def location(self):
        return self.PATHNAME.format(source=self.alias.handle)

    @location.setter
    def location(self, value):
        try:
            self.nickname = re.search('^{}$'.format(
                self.PATHNAME.format(source='(\w+)/?')), value).group(1)
        except AttributeError:
            raise AttributeError("'Location' attibute is malformed.")

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self):
        if not self._onegeo:
            self._onegeo = onegeo_manager.Source(self.uri, self.protocol)
        return self._onegeo

    @onegeo.setter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self, *args, **kwargs):
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

        if self.protocol not in dict(self.PROTOCOL_CHOICES).keys():
            raise ValidationError("'protocol' input parameters is unauthorized.")

        super().save(*args, **kwargs)
