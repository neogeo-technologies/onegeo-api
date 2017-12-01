from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from importlib import import_module
import uuid

from onegeo_api.utils import clean_my_obj


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


class SearchModel(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250, unique=True)
    config = JSONField("Config", blank=True, null=True)

    # FK & alt
    user = models.ForeignKey(User, blank=True, null=True)
    context = models.ManyToManyField("onegeo_api.Context")

    def save(self, *args, **kwargs):
        Context = apps.get_model(app_label='onegeo_api', model_name='Context')
        set_names_ctx = Context.objects.all()
        for c in set_names_ctx:
            if self.name == c.name:
                raise ValidationError("Un modèle de recherche ne peut avoir "
                                      "le même nom qu'un contexte d'indexation.")
        super().save(*args, **kwargs)

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @classmethod
    def get_from_uuid(cls, uuid, user=None):
        if user:
            search_models = cls.objects.filter(user=user)
        else:
            search_models = cls.objects.all()
        for sm in search_models:
            if str(sm.uuid)[:len(uuid)] == uuid:
                return sm
        return None

    @classmethod
    def get_from_params(cls, params):
        try:
            search_model = cls.objects.get(**params)
        except:
            return None
        else:
            return search_model

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

    @classmethod
    def custom_delete(cls, name, user):
        obj = cls.get_from_params({'name': name})
        if not obj:
            data = {"error": "Echec de la suppression: Aucun model de recherche ne correspond à cet identifiant."}
            status = 404
        elif obj and obj.user == user:
            obj.delete()
            data = {}
            status = 204
        else:
            data = {"error": "Echec de la suppression: Vous n'etes pas l'usager de ce modèle de recherche."}
            status = 403
        return JsonResponse(data, status=status)
