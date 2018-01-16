from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.http import Http404

from onegeo_api.models.abstracts import AbstractModelAnalyzis
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import slash_remove


class Analyzer(AbstractModelAnalyzis):

    filters = models.ManyToManyField("Filter")
    tokenizer = models.ForeignKey("Tokenizer", blank=True, null=True)

    def save(self, *args, **kwargs):
        kwargs['model_name'] = 'Analyzer'
        return super().save(*args, **kwargs)

    @property
    def detail_renderer(self):

        filt_names = [f.name for f in self.filters.all().order_by("name")]
        return clean_my_obj({
            "location": "analyzers/{0}".format(self.name),
            "name": self.name,
            "alias": self.alias.handle,
            "config": self.config or None,
            "tokenfilters": filt_names or None,
            "reserved": self.reserved,
            "tokenizer": self.tokenizer and self.tokenizer.name or None})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(Q(user=user) | Q(user=None)).order_by("reserved", "name")
        return [obj.detail_renderer for obj in instances]

    @classmethod
    def create_with_response(cls, request, defaults, filters):
        instance = cls.objects.create(**defaults)

        if len(filters) > 0:
            instance.filters.set(filters, clear=True)

        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response["Location"] = "{0}/{1}".format(uri, instance.alias.handle)

        return response

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle__startswith=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun analyseur ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cet analyseur")
        return instance


class Filter(AbstractModelAnalyzis):

    def save(self, *args, **kwargs):
        kwargs['model_name'] = 'Filter'
        return super().save(*args, **kwargs)

    @property
    def detail_renderer(self):
        return clean_my_obj({"location": "tokenfilters/{0}".format(self.name),
                             "name": self.name,
                             "alias": self.alias.handle,
                             "config": self.config or None,
                             "reserved": self.reserved})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(Q(user=user) | Q(user=None)).order_by("reserved", "name")
        return [filter.detail_renderer for filter in instances]

    @classmethod
    def create_with_response(cls, request, defaults):
        instance = cls.objects.create(**defaults)

        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response["Location"] = "{0}/{1}".format(uri, instance.alias.handle)

        return response

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun filtre ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à ce filtre")
        return instance


class Tokenizer(AbstractModelAnalyzis):

    def save(self, *args, **kwargs):
        kwargs['model_name'] = 'Tokenizer'
        return super().save(*args, **kwargs)

    @property
    def detail_renderer(self):
        return clean_my_obj({"location": "tokenizers/{0}".format(self.name),
                             "name": self.name,
                             "alias": self.alias.handle,
                             "config": self.config or None,
                             "reserved": self.reserved})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [token.detail_renderer for token in instances]

    @classmethod
    def create_with_response(cls, request, defaults):
        instance = cls.objects.create(**defaults)
        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response["Location"] = "{0}/{1}".format(uri, instance.alias.handle)
        return response

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun jeton ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à ce jeton")
        return instance
