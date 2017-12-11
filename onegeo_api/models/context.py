from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.http import JsonResponse

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

    # FK & alt
    resources = models.ManyToManyField("onegeo_api.Resource")

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

    def access_allowed(self, user):
        for resource in self.resources.all():
            if resource.source.user != user:
                return False
        return True

    def update_clmn_properties(self, list_ppt_clt):
        for ppt in self.clmn_properties:
            for ppt_clt in list_ppt_clt:
                if ppt["name"] == ppt_clt["name"]:
                    ppt.update(ppt_clt)

    @classmethod
    def get_with_permission(cls, short_uuid, user):
        instance = cls.cust_obj.get_or_not_found(short_uuid)
        if not instance.access_allowed(user):
            raise PermissionDenied
        return instance

    @property
    def detail_renderer(self):

        return {"location": "/indexes/{}".format(self.short_uuid),
                "resource": ["/sources/{}/resources/{}".format(
                    r.source.short_uuid, r.short_uuid) for r in self.resources.all()],
                "columns": self.clmn_properties,
                "name": self.name,
                "reindex_frequency": self.reindex_frequency}

    @classmethod
    def list_renderer(cls, user):

        Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
        contexts = cls.objects.filter(
            resources__in=Resource.objects.filter(source__user=user))

        return [ctx.detail_renderer for ctx in contexts]

    @classmethod
    def create_with_response(cls, request, name, clmn_properties, reindex_frequency, resource):
        try:
            context = Context.objects.create(name=name,
                                             clmn_properties=clmn_properties,
                                             reindex_frequency=reindex_frequency)
        except ValidationError as e:
            return JsonResponse(data={"error": e.message}, status=409)

        context.resources.add(resource)
        response = JsonResponse(data={}, status=201)
        uri = slash_remove(request.build_absolute_uri())
        response['Location'] = '{}/{}'.format(uri, context.short_uuid)

        return response

    @classmethod
    def delete_with_response(cls, uuid, user):
        instance = cls.cust_obj.get_or_not_found(uuid)
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
