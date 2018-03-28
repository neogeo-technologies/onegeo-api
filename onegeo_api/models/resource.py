from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.db import models
from onegeo_api.models.abstracts import AbstractModelProfile


class Resource(AbstractModelProfile):

    class Meta(object):
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'

    columns = JSONField(verbose_name='Columns')

    source = models.ForeignKey(
        to='Source', verbose_name='Source', on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None

    @property
    def indexes(self):
        return self.indexprofile_set.all()

    @property
    def location(self):
        return '/sources/{}/resources/{}'.format(
            self.source.alias.handle, self.alias.handle)

    @location.setter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self, *args, **kwargs):
        if not self._onegeo:
            print('resource_onegeo')
            self._onegeo = self.source.onegeo.get_resources(names=[self.name])[0]
        return self._onegeo

    @onegeo.setter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self, **kwargs):
        return {
            'columns': self.columns,
            'indexes': [m.location for m in self.indexes],
            'location': self.location,
            'name': self.name or self.alias.handle}

    @classmethod
    def list_renderer(cls, nickname, user, **kwargs):
        model = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = model.get_or_raise(nickname, user)
        return [
            item.detail_renderer(**kwargs)
            for item in cls.objects.filter(source=source).order_by('name')]
