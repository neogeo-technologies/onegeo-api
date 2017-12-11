from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models

import uuid


class AbstractModelAnalyzis(models.Model):
    """
        Héritée par modeles: Analyzer, Filter, Tokenizer
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250, unique=True)
    user = models.ForeignKey(User, blank=True, null=True)
    config = JSONField("Config", blank=True, null=True)
    reserved = models.BooleanField("Reserved", default=False)

    class Meta:
        abstract = True

    def __unicode__(self):
            return self.name

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @property
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
    def custom_filter(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_from_name(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def get_with_permission(cls, *args, **kwargs):
        raise NotImplemented


class AbstractModelProfile(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250, unique=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

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
    def get_with_permission(cls, *args, **kwargs):
        raise NotImplemented
