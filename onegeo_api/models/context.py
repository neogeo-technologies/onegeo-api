from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.http import JsonResponse
import uuid


from onegeo_api.elasticsearch_wrapper import elastic_conn


class Context(models.Model):

    RF_L = (
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("monthly", "monthly"),)

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250)
    clmn_properties = JSONField("Columns")
    reindex_frequency = models.CharField("Reindex_frequency", choices=RF_L,
                                         default="monthly", max_length=250)

    # FK & alt
    resources = models.ManyToManyField("onegeo_api.Resource")

    def save(self, *args, **kwargs):
        SearchModel = apps.get_model(app_label='onegeo_api', model_name='SearchModel')
        set_names_sm = SearchModel.objects.all()
        for s in set_names_sm:
            if self.name == s.name:
                raise ValidationError("Un contexte d'indexation ne peut avoir "
                                      "le même nom qu'un modèle de recherche.")
        super().save(*args, **kwargs)

    def user_allowed(self, user):
        for resource in self.resources.all():
            if resource.source.user != user:
                return False
        return True

    def update_clmn_properties(self, list_ppt_clt):
        for ppt in self.clmn_properties:
            for ppt_clt in list_ppt_clt:
                if ppt["name"] == ppt_clt["name"]:
                    ppt.update(ppt_clt)

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @classmethod
    def get_from_uuid(cls, uuid, user=None):
        Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
        if user:
            contexts = cls.objects.filter(
                resources__in=Resource.objects.filter(source__user=user))
        else:
            contexts = cls.objects.all()
        for ctx in contexts:
            if str(ctx.uuid)[:len(uuid)] == uuid:
                return ctx
        return None

    @property
    def format_data(self):
        return {"location": "/indexes/{}".format(self.short_uuid),
                "resource": ["/sources/{}/resources/{}".format(
                    r.source.short_uuid, r.short_uuid) for r in self.resources.all()],
                "columns": self.clmn_properties,
                "name": self.name,
                "reindex_frequency": self.reindex_frequency}

    @classmethod
    def format_by_filter(cls, user):
        Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
        contexts = cls.objects.filter(
            resources__in=Resource.objects.filter(source__user=user))
        return [ctx.format_data for ctx in contexts]

    @classmethod
    def custom_delete(cls, uuid, user):
        obj = cls.get_from_uuid(uuid)
        if not obj:
            data = {"error": "Echec de la suppression: Aucun context ne correspond à cet identifiant."}
            status = 404
        elif obj and obj.user == user:
            obj.delete()
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
