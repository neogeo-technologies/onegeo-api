from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from onegeo_api.models import AbstractModelAnalyzis
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import slash_remove


class RelatedFilters(models.Model):
    analyzer = models.ForeignKey("Analyzer")
    filter = models.ForeignKey("Filter")


class Analyzer(AbstractModelAnalyzis):

    filters = models.ManyToManyField("Filter", through="RelatedFilters", blank=True)
    tokenizer = models.ForeignKey("Tokenizer", blank=True, null=True)

    @property
    def detail_renderer(self):

        filt_names = [f.name for f in self.filters.all().order_by("name")]
        return clean_my_obj({
            "location": "analyzers/{0}".format(self.name),
            "name": self.name,
            "config": self.config or None,
            "tokenfilters": filt_names or None,
            "reserved": self.reserved,
            "tokenizer": self.tokenizer and self.tokenizer.name or None})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [analyzer.detail_renderer for analyzer in instances]

    @classmethod
    def create_with_response(cls, request, name, user, config, filters, tokenizer):
        analyzer, created = cls.objects.get_or_create(
            name=name, defaults={"user": user, "config": config})
        if created and len(filters) > 0:
            for f in filters:
                try:
                    flt = Filter.objects.get(name=f)
                    analyzer.filter.add(flt)
                    analyzer.save()
                except Filter.DoesNotExist:
                    return JsonResponse({"error": "Echec de création de l'analyseur. La liste contient un ou plusieurs filtres n'existant pas. "}, status=400)

        if created and tokenizer:
            try:
                tkn_chk = Tokenizer.objects.get(name=tokenizer)
                analyzer.tokenizer = tkn_chk
                analyzer.save()
            except Tokenizer.DoesNotExist:
                return JsonResponse({"error": "Echec de création de l'analyseur: Le tokenizer n'existe pas. "}, status=400)

        status = created and 201 or 409
        if created:
            response = JsonResponse(data={}, status=status)
            uri = slash_remove(request.build_absolute_uri())
            response["Location"] = "{0}/{1}".format(uri, analyzer.short_uuid)
        if created is False:
            data = {"error": "Echec de la création: L'élément est déjà existant."}

        return JsonResponse(data=data, status=status)

    @classmethod
    def delete_with_response(cls, name, user):

        instance = cls.get_with_permission(name, user)
        if instance.reserved is False:
            instance.delete()
            status = 204
            data = {}
        else:
            status = 405
            data = {"error": "Suppression impossible: L'usage de cet élément est réservé."}

        return JsonResponse(data, status=status)

    @classmethod
    def custom_filter(cls, user):
        instances = cls.objects.filter(Q(user=user) | Q(user=None)).order_by("reserved", "name")
        return [obj.detail_renderer for obj in instances]

    @classmethod
    def get_from_name(cls, name):
        return get_object_or_404(cls, name=name)

    @classmethod
    def get_with_permission(cls, name, user):
        instance = cls.get_from_name(name)
        if instance.user != user:
            raise PermissionDenied
        return instance


class Filter(AbstractModelAnalyzis):

    @property
    def detail_renderer(self):
        return clean_my_obj({"location": "tokenfilters/{0}".format(self.name),
                             "name": self.name,
                             "config": self.config or None,
                             "reserved": self.reserved})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [flt.detail_renderer for flt in instances]

    @classmethod
    def create_with_response(cls, request, name, user, config):
        filter, created = cls.objects.get_or_create(
            name=name, defaults={"config": config, "user": user})

        status = created and 201 or 409
        if created:
            response = JsonResponse(data={}, status=status)
            uri = slash_remove(request.build_absolute_uri())
            response["Location"] = "{0}/{1}".format(uri, filter.short_uuid)
        if created is False:
            data = {"error": "Echec de la création: L'élément est déjà existant."}

        return JsonResponse(data=data, status=status)

    @classmethod
    def delete_with_response(cls, name, user):

        instance = cls.get_with_permission(name, user)
        if instance.reserved is False:
            instance.delete()
            status = 204
            data = {}
        else:
            status = 405
            data = {"error": "Suppression impossible: L'usage de cet élément est réservé."}

        return JsonResponse(data, status=status)

    @classmethod
    def get_from_name(cls, name):
        return get_object_or_404(cls, name=name)

    @classmethod
    def get_with_permission(cls, name, user):
        instance = cls.get_from_name(name)
        if instance.user != user:
            raise PermissionDenied
        return instance


class Tokenizer(AbstractModelAnalyzis):

    @property
    def detail_renderer(self):
        return clean_my_obj({"location": "tokenizers/{0}".format(self.name),
                             "name": self.name,
                             "config": self.config or None,
                             "reserved": self.reserved})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [token.detail_renderer for token in instances]

    @classmethod
    def create_with_response(cls, request, name, user, config):
        filter, created = cls.objects.get_or_create(
            name=name, defaults={"config": config, "user": user})

        status = created and 201 or 409
        if created:
            response = JsonResponse(data={}, status=status)
            uri = slash_remove(request.build_absolute_uri())
            response["Location"] = "{0}/{1}".format(uri, filter.short_uuid)
        if created is False:
            data = {"error": "Echec de la création: L'élément est déjà existant."}

        return JsonResponse(data=data, status=status)

    @classmethod
    def delete_with_response(cls, name, user):

        instance = cls.get_with_permission(name, user)
        if instance.reserved is False:
            instance.delete()
            status = 204
            data = {}
        else:
            status = 405
            data = {"error": "Suppression impossible: L'usage de cet élément est réservé."}

        return JsonResponse(data, status=status)

    @classmethod
    def get_from_name(cls, name):
        return get_object_or_404(cls, name=name)

    @classmethod
    def get_with_permission(cls, name, user):
        instance = cls.get_from_name(name)
        if instance.user != user:
            raise PermissionDenied
        return instance
