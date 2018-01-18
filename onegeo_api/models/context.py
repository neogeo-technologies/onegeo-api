from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import models

from django.http import JsonResponse
from django.http import Http404

from onegeo_api.models.abstracts import AbstractModelProfile
from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import slash_remove

# from onegeo_api.elasticsearch_wrapper import elastic_conn


class Context(AbstractModelProfile):

    RF_L = (
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("monthly", "monthly"),)

    clmn_properties = JSONField("Columns")
    reindex_frequency = models.CharField("Reindex_frequency", choices=RF_L,
                                         default="monthly", max_length=250)

    class Meta:
        verbose_name = "Contexte"

    def save(self, *args, **kwargs):

        kwargs['model_name'] = 'Context'

        SearchModel = apps.get_model(app_label='onegeo_api', model_name='SearchModel')
        if SearchModel.objects.filter(name=self.name).exists():
            raise ValidationError("Un contexte d'indexation ne peut avoir "
                                  "le même nom qu'un modèle de recherche.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        Task = apps.get_model(app_label='onegeo_api', model_name='Task')
        Task.objects.filter(model_type_alias=self.alias.handle, model_type="Context").delete()
        # elastic_conn.delete_index_by_alias(instance.name) #Erreur sur l'attribut indices à None
        return super().delete(*args, **kwargs)

    @property
    def resource(self):
        return self.resource_set.get(context=self)

    def update_clmn_properties(self, list_ppt_clt):
        for ppt in self.clmn_properties:
            for ppt_clt in list_ppt_clt:
                if ppt["name"] == ppt_clt["name"]:
                    ppt.update(ppt_clt)

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucun context d'indexation ne correspond à votre requête")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à ce contexte d'indexation")
        return instance

    @property
    def detail_renderer(self):
        d = {
            "location": "/indexes/{}".format(self.alias.handle),
            "resource": "/sources/{}/resources/{}".format(
                self.resource.source.alias.handle, self.resource.alias.handle),
            "columns": self.clmn_properties,
            "name": self.name,
            "alias": self.alias.handle,
            "reindex_frequency": self.reindex_frequency}
        return clean_my_obj(d)

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [context.detail_renderer for context in instances]

    @classmethod
    def create_with_response(cls, request, defaults, resource):

        instance = Context.objects.create(**defaults)

        resource.context = instance
        try:
            resource.save()
        except Exception as e:
            instance.delete()
            return JsonResponse(data={"error": e.message}, status=409)

        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{}/{}'.format(uri, instance.alias.handle)

        return response
