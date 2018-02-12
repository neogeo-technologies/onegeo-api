from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.http import JsonResponse
# from importlib import import_module
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

    def detail_renderer(self, include=False, cascading=False, **others):
        opts = {'include': cascading and include, 'cascading': cascading}

        # try:
        #     ext = import_module(
        #         'onegeo_api.extensions.{0}'.format(self.name), __name__)
        #     response['extended'] = True
        # except ImportError:
        #     ext = import_module('onegeo_api.extensions.__init__', __name__)
        # finally:
        #     plugin = ext.plugin(
        #         self.config, [ctx for ctx in self.index_profiles.all()])
        #     if plugin.qs:
        #         response['qs_params'] = [
        #             {'key': e[0], 'description': e[1], 'type': e[2]}
        #             for e in plugin.qs]

        return {
            'config': self.config,
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

    @classmethod
    def get_from_params(cls, params):
        try:
            search_model = cls.objects.get(**params)
        except Exception:
            return None
        else:
            return search_model

    @property
    def get_available_index_profiles_from_alias(self, index_profiles_aliases, user):
        IndexProfile = apps.get_model(app_label='onegeo_api', model_name='IndexProfile')
        Task = apps.get_model(app_label='onegeo_api', model_name='Task')

        index_profiles_available = []
        for alias in index_profiles_aliases:
            try:
                # index_profile = IndexProfile.get_with_permission(alias, user)  # Si restriction sur user
                index_profile = IndexProfile.objects.get(alias__handle=alias)
            except Exception:
                raise
            if Task.objects.filter(alias__handle=index_profile.alias.handle,
                                   user=user,
                                   stop_date=None).exists():
                raise MultiTaskError()
            else:
                index_profiles_available.append(index_profile)
        return index_profiles_available

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
