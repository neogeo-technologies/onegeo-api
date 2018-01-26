from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import models
from django.http import JsonResponse
from django.http import Http404
from importlib import import_module

from onegeo_api.exceptions import MultiTaskError
from onegeo_api.utils import clean_my_obj
from onegeo_api.models.abstracts import AbstractModelProfile


class SearchModel(AbstractModelProfile):

    config = JSONField("Config", blank=True, null=True)

    # FK & alt
    user = models.ForeignKey(User, blank=True, null=True)
    index_profiles = models.ManyToManyField("onegeo_api.IndexProfile")

    def save(self, *args, **kwargs):
        kwargs['model_name'] = 'SearchModel'
        return super().save(*args, **kwargs)

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun modèle de recherche ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à ce modèle de recherche")
        return instance

    @classmethod
    def get_from_params(cls, params):
        try:
            search_model = cls.objects.get(**params)
        except:
            return None
        else:
            return search_model

    @property
    def detail_renderer(self):
        response = {
            "location": "profiles/{}".format(self.name),
            "name": self.name,
            "alias": self.alias.handle,
            "config": self.config,
            "indexes": ["/indexes/{}".format(ctx.alias.handle) for ctx in self.index_profiles.all()]}

        try:
            ext = import_module('onegeo_api.extensions.{0}'.format(self.name), __name__)
            response['extended'] = True
        except ImportError:
            ext = import_module('onegeo_api.extensions.__init__', __name__)
        finally:
            plugin = ext.plugin(self.config, [ctx for ctx in self.index_profiles.all()])
            if plugin.qs:
                response['qs_params'] = [{'key': e[0],
                                          'description': e[1],
                                          'type': e[2]} for e in plugin.qs]

        return clean_my_obj(response)

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [search_model.detail_renderer for search_model in instances]

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
