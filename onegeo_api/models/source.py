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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None

    @property
    def location(self):
        return '/sources/{}'.format(self.alias.handle)

    @location.setter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self):
        if not self._onegeo:
            print('source_onegeo')
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
        # import pdb; pdb.set_trace()

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
        if 'data' in kwargs:
            data = kwargs['data']
            # à améliorer seul moyen pour ne coller au modele abstrait et
            # mettre à jour les champs de la source
            kwargs.pop('data')
            # mise à jour de la tache
            tasks = Task.objects.filter(user=self.user, name=self.name,
                                        alias=self.alias, description="1")
            # # update des ressources
            rsr = self.resource_set.all()
            if 'location' in data:
                self.alias.handle = data['location'].split('/')[-1]
            if 'name' in data:
                self.name = data['name']
            rsr.update(source=self)
            # update de la tache (1 ou x??)
            for task in tasks:
                task.name = self.name
                task.alias = self.alias
                task.save()
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
            # creation d'une source / tache celery
            task = Task.objects.create(user=self.user, name=self.name,
                                       alias=self.alias, description="1")
            create_resources_with_log.apply_async(
                kwargs={'pk': self.pk}, task_id=str(task.celery_id))
