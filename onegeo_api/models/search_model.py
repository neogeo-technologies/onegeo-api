from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.http import JsonResponse
from onegeo_api.exceptions import MultiTaskError
from onegeo_api.models.abstracts import AbstractModelProfile
import re


class SearchModel(AbstractModelProfile):

    class Meta(object):
        verbose_name = 'Search Model'
        verbose_name_plural = 'Search Models'

    config = JSONField(
        verbose_name='Query DSL', blank=True, null=True)

    user = models.ForeignKey(
        to=User, verbose_name='User', blank=True, null=True)

    index_profiles = models.ManyToManyField(
        to='IndexProfile', verbose_name='Indexation profiles')

    @property
    def location(self):
        return '/services/{}'.format(self.alias.handle)

    @location.setter
    def location(self):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self, include=False, cascading=False, **others):
        opts = {'include': cascading and include, 'cascading': cascading}
        indexes_list = list(self.index_profiles.values_list('name'))
        return {
            'config': self.config,
            'indexes_list': indexes_list,
            'indexes': [
                m.detail_renderer(**opts) if include else m.location
                for m in self.index_profiles.all()],
            'location': self.location,
            'name': self.name}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [
            search_model.detail_renderer(**opts)
            for search_model in cls.objects.filter(user=user)]

    def save(self, *args, **kwargs):

        if not self.name:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if not re.match('^[\w\s]+$', self.name):
            raise ValidationError("Malformed 'name' parameter.")

        return super().save(*args, **kwargs)

    # TODO(cbenhabib): A implementer pour remplacer:
    # get_search_model(), get_index_profiles_obj(), set_search_model_index_profiles()
    @classmethod
    def custom_create(cls, name, user, config):
        error = None
        sm = None
        try:
            sm, created = cls.objects.get_or_create(
                name=name, defaults={"user": user, "config": config})
        except ValidationError as e:
            error = JsonResponse({"error": e.message}, status=409)
        if created is False:
            error = JsonResponse(data={"error": "Conflict"}, status=409)

        return sm, error
