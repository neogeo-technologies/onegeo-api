from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db import models
from django.http import Http404
import inspect
from onegeo_api.utils import clean_my_obj
import uuid


class Alias(models.Model):
    """Table des alias (nickname) à utiliser sur l'ensemble des modèles."""

    # Construire MODELS_CHOICES avec __all__ de __init__
    MODELS_CHOICES = (
        ('Undefined', 'Undefined'),
        ('Analyzer', 'Analyzer'),
        ('IndexProfile', 'IndexProfile'),
        ('Filter', 'Filter'),
        ('Resource', 'Resource'),
        ('SearchModel', 'SearchModel'),
        ('Source', 'Source'),
        ('Tokenizer', 'Tokenizer'))  # Undefined ???

    uuid = models.UUIDField(
        verbose_name='UUID', default=uuid.uuid4,
        primary_key=True, editable=False)

    handle = models.CharField(
        verbose_name='Nickname', max_length=250, unique=True)

    model_name = models.CharField(
        verbose_name='Model', max_length=30,
        choices=MODELS_CHOICES, default=MODELS_CHOICES[0][0])

    def __str__(self):
        return self.handle

    def save(self, *args, **kwargs):
        # Si creation sans alias depuis les modeles.
        if not self.handle:
            self.handle = str(self.uuid)[:7]
        return super().save(*args, **kwargs)

    @classmethod
    def custom_create(cls, model_name, handle=None):
        return cls.objects.create(**clean_my_obj({"model_name": model_name, "handle": handle}))

    def update_handle(self, new_handle):
        self.handle = new_handle
        self.save()

    @classmethod
    def updating_is_allowed(cls, new_handle, current_handle):
        if new_handle != current_handle:
            if cls.objects.filter(handle=new_handle).exists():
                return False
        return True

    @classmethod
    def get_related_instance(cls, alias, user):
        Model_r = apps.get_model(app_label='onegeo_api', model_name=alias.model_name)
        try:
            instance = Model_r.get_with_permission(alias.handle, user)
        except Exception as error:
            raise error
        return instance

    @classmethod
    def get_or_not_found(cls, alias, user):
        try:
            instance = cls.objects.get(handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun alias ne correspond à votre requête")
        return instance


class AbstractModelAnalyzis(models.Model):
    """Héritée par les modèles: Analyzer, Filter, Tokenizer."""

    name = models.CharField(
        verbose_name="Name", max_length=250, unique=True)

    user = models.ForeignKey(User, verbose_name="User", blank=True, null=True)

    config = JSONField(
        verbose_name='Configuration', blank=True, null=True)

    reserved = models.BooleanField(
        verbose_name='Reserved', default=False)

    alias = models.OneToOneField(
        to="Alias", on_delete=models.CASCADE)

    class Meta(object):
        abstract = True

    def __unicode__(self):
            return self.name

    def save(self, *args, **kwargs):
        model_name = kwargs.pop('model_name', 'Undefined')

        # "if not self.alias" retourne une erreur RelatedObjectDoesNotExist ??
        if not self.alias_id:
            self.alias = Alias.objects.create(model_name=model_name)
        return super().save(*args, **kwargs)

    def detail_renderer(self):
        raise NotImplemented

    @classmethod
    def list_renderer(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def create_with_response(cls, *args, **kwargs):
        raise NotImplemented

    @property
    def delete_with_response(self):
        raise NotImplemented

    @classmethod
    def get_with_permission(cls, *args, **kwargs):
        raise NotImplemented


class AbstractModelProfile(models.Model):

    _nickname = None

    alias = models.OneToOneField(
        to='Alias', verbose_name='Nickname', on_delete=models.CASCADE)

    name = models.TextField(
        verbose_name='Name', blank=True, null=True)

    description = models.TextField(
        verbose_name='Description', blank=True, null=True)

    user = models.ForeignKey(to=User, blank=True, null=True)

    class Meta(object):
        abstract = True

    def __str__(self):
        return self.alias.handle

    def __unicode__(self):
        return self.name or self._nickname

    @property
    def nickname(self):
        return self._nickname

    @nickname.setter
    def nickname(self, value):
        if self.alias.handle != value \
                and Alias.objects.filter(handle=value).exists():
            raise IntegrityError('This Nickname is already in use.')
        self._nickname = value

    def save(self, *args, **kwargs):

        try:
            self.alias.handle = self.nickname
        except Exception as error:
            if error.__class__.__qualname__ == 'RelatedObjectDoesNotExist':
                stack = inspect.stack()
                caller = stack[1][0].f_locals['self'].__class__.__qualname__
                self.alias = Alias.objects.create(
                    handle=self.nickname, model_name=caller)
            else:
                raise error
        else:
            self.alias.save()

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # suppression de la tache lié à la source
        Task = apps.get_model(app_label='onegeo_api', model_name='Task')
        Task.objects.filter(alias=self.alias).delete()
        return super().delete(*args, **kwargs)

    @property
    def location(self):
        raise NotImplemented

    @property
    def detail_renderer(self):
        raise NotImplemented

    @classmethod
    def list_renderer(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def create_with_response(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_from_uuid(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_from_name(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_or_raise(cls, nickname, user):

        # TODO
        # alias = Alias.objects.filter(handle=nickname, uuid=nickname)
        # print(alias)

        try:
            instance = cls.objects.get(alias__handle=nickname)
        except cls.DoesNotExist:
            raise Http404()
        if instance.user != user:
            raise PermissionDenied()
        return instance
