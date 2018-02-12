from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from onegeo_api.models.abstracts import AbstractModelProfile
import onegeo_manager
import re


class IndexProfile(AbstractModelProfile):

    class Meta(object):
        verbose_name = 'Indexation Profile'
        verbose_name_plural = 'Indexation Profiles'

    REINDEX_FREQUENCY_CHOICES = (
        ('monthly', 'monthly'),
        ('weekly', 'weekly'),
        ('daily', 'daily'))

    clmn_properties = JSONField(
        verbose_name='Columns', blank=True, null=True)

    reindex_frequency = models.CharField(
        verbose_name='Re-indexation frequency',
        choices=REINDEX_FREQUENCY_CHOICES,
        default=REINDEX_FREQUENCY_CHOICES[0][0],
        max_length=250)

    resource = models.ForeignKey(
        to='Resource', verbose_name='Resource')

    @property
    def location(self):
        return '/indexes/{}'.format(self.alias.handle)

    @property
    def onegeo(self):
        return onegeo_manager.IndexProfile('foo', self.resource.onegeo)  # TODO: foo name

    def detail_renderer(self, include=False, cascading=False, **others):
        return {
            'columns': self.clmn_properties,
            'location': self.location,
            'name': self.name,
            'reindex_frequency': self.reindex_frequency,
            'resource': include and self.resource.detail_renderer(
                include=cascading and include, cascading=cascading)
            or self.resource.location}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [item.detail_renderer(**opts)
                for item in cls.objects.filter(user=user)]

    def save(self, *args, **kwargs):

        if not self.name or not self.resource:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if not re.match('^[\w\s]+$', self.name):
            raise ValidationError("Malformed 'name' parameter.")

        # TODO Mettre à jour les propriétés de colonnes
        self.clmn_properties = [
            prop.all() for prop in self.onegeo.iter_properties()]

        return super().save(*args, **kwargs)
