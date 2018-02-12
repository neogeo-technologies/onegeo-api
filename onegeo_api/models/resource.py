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

    @property
    def indexes(self):
        return self.indexprofile_set.all()

    @property
    def location(self):
        return '/sources/{}/resources/{}'.format(
            self.source.alias.handle, self.alias.handle)

    @property
    def onegeo(self):
        return self.source.onegeo.get_resources(names=[self.name])[0]

    def detail_renderer(self, **kwargs):
        return {
            'columns': self.columns,
            'indexes': [m.location for m in self.indexes],
            'location': self.location,
            'name': self.name}

    @classmethod
    def list_renderer(cls, nickname, user, **kwargs):
        model = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = model.get_or_raise(nickname, user)
        return [
            item.detail_renderer(**kwargs)
            for item in cls.objects.filter(source=source).order_by('name')]
