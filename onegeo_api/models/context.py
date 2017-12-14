from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.http import JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404

from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.models import AbstractModelProfile
from onegeo_api.utils import slash_remove


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
        SearchModel = apps.get_model(app_label='onegeo_api', model_name='SearchModel')
        set_names_sm = SearchModel.objects.all()
        for s in set_names_sm:
            if self.name == s.name:
                raise ValidationError("Un contexte d'indexation ne peut avoir "
                                      "le même nom qu'un modèle de recherche.")
        super().save(*args, **kwargs)

    @property
    def resources(self):
        Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
        return Resource.objects.filter(context=self)

    def update_clmn_properties(self, list_ppt_clt):
        for ppt in self.clmn_properties:
            for ppt_clt in list_ppt_clt:
                if ppt["name"] == ppt_clt["name"]:
                    ppt.update(ppt_clt)

    @classmethod
    def get_from_uuid(cls, short_uuid):
        for obj in cls.objects.all():
            if str(obj.uuid)[:len(short_uuid)] == short_uuid:
                return obj
        raise Http404

    @classmethod
    def get_from_name(cls, name):
        return get_object_or_404(cls, name=name)

    @classmethod
    def get_with_permission(cls, short_uuid, user):
        instance = cls.get_from_uuid(short_uuid)
        if instance.user != user:
            raise PermissionDenied
        return instance

    @property
    def detail_renderer(self):

        return {"location": "/indexes/{}".format(self.short_uuid),
                "resource": ["/sources/{}/resources/{}".format(
                    r.source.short_uuid, r.short_uuid) for r in self.resources],
                "columns": self.clmn_properties,
                "name": self.name,
                "reindex_frequency": self.reindex_frequency}

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user)
        return [context.detail_renderer for context in instances]

    @classmethod
    def create_with_response(cls, request, name, clmn_properties, reindex_frequency, resources):
        try:
            context = Context.objects.create(name=name,
                                             user=request.user,
                                             clmn_properties=clmn_properties,
                                             reindex_frequency=reindex_frequency)
        except ValidationError as e:
            return JsonResponse(data={"error": e.message}, status=409)

        for resource in resources:
            resource.context = context
            try:
                resource.save()
            except Exception as e:
                return JsonResponse(data={"error": e.message}, status=409)

        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{}/{}'.format(uri, context.short_uuid)

        return response

    @classmethod
    def delete_with_response(cls, uuid, user):
        instance = cls.get_or_not_found(uuid)
        if not instance:
            data = {"error": "Echec de la suppression: Aucun context ne correspond à cet identifiant."}
            status = 404
        elif instance.access_allowed(user):
            instance.delete()
            data = {}
            status = 204
        else:
            data = {"error": "Echec de la suppression: Vous n'etes pas l'usager de ce context."}
            status = 403
        return JsonResponse(data, status=status)


@receiver(post_delete, sender=Context)
def on_delete_context(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Task.objects.filter(model_type_id=instance.uuid, model_type="context").delete()
    elastic_conn.delete_index_by_alias(instance.name)
