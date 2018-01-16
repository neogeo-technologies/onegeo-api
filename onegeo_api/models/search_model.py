from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404
from importlib import import_module

from onegeo_api.exceptions import MultiTaskError
from onegeo_api.utils import clean_my_obj
from onegeo_api.models.abstracts import AbstractModelProfile


class SearchModel(AbstractModelProfile):

    config = JSONField("Config", blank=True, null=True)

    # FK & alt
    user = models.ForeignKey(User, blank=True, null=True)
    contexts = models.ManyToManyField("onegeo_api.Context")

    def save(self, *args, **kwargs):

        kwargs['model_name'] = 'SearchModel'

        Context = apps.get_model(app_label='onegeo_api', model_name='Context')
        if Context.objects.filter(name=self.name).exists():
            raise ValidationError("Un modèle de recherche ne peut avoir "
                                  "le même nom qu'un contexte d'indexation.")
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
            "indexes": [ctx.alias.handle for ctx in self.contexts]}

        try:
            ext = import_module('..extensions.{0}'.format(self.name), __name__)
            response['extended'] = True
        except ImportError:
            ext = import_module('..extensions.__init__', __name__)
        finally:
            plugin = ext.plugin(self.config, [ctx for ctx in self.contexts])
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
    def get_available_contexts_from_alias(self, contexts_aliases, user):
        Context = apps.get_model(app_label='onegeo_api', model_name='Context')
        Task = apps.get_model(app_label='onegeo_api', model_name='Task')

        contexts_available = []
        for alias in contexts_aliases:
            try:
                # ctx = Context.get_with_permission(alias, user)  # Si restriction sur user
                ctx = Context.objects.get(alias__handle=alias)
            except Exception:
                raise
            if Task.objects.filter(model_type="context",
                                   model_type_alias=ctx.alias.handle,
                                   user=user,
                                   stop_date=None).exists():
                raise MultiTaskError()
            else:
                contexts_available.append(ctx)
        return contexts_available

    #To be eradicated
    @property
    def format_data(self):

        def retreive_contexts(name):
            smc = SearchModel.context.through
            set = smc.objects.filter(searchmodel__name=name)
            return [s.context.name for s in set if s.context.name is not None]

        response = {
            "location": "profiles/{}".format(self.name),
            "name": self.name,
            "config": self.config,
            "indexes": retreive_contexts(self.name)}

        contexts = [e.context for e in
                    SearchModel.context.through.objects.filter(searchmodel=self)]

        try:
            ext = import_module('..extensions.{0}'.format(self.name), __name__)
            response['extended'] = True
        except ImportError:
            ext = import_module('..extensions.__init__', __name__)
        finally:
            plugin = ext.plugin(self.config, contexts)
            if plugin.qs:
                response['qs_params'] = [{'key': e[0],
                                          'description': e[1],
                                          'type': e[2]} for e in plugin.qs]

        return clean_my_obj(response)

    @classmethod
    def custom_filter(cls, user):
        search_model = SearchModel.objects.filter(Q(user=user) | Q(user=None)).order_by("name")
        return [sm.format_data for sm in search_model]

    @classmethod
    def user_access(cls, name, user):
        sm = get_object_or_404(cls, name=name)
        if sm.user != user:
            raise PermissionDenied
        return sm

    # TODO(cbenhabib): A implementer pour remplacer:
    # get_search_model(), get_contexts_obj(), set_search_model_contexts()
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
