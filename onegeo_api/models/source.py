from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.utils import timezone
from re import search
from threading import Thread
import uuid

from onegeo_manager.source import Source as OnegeoSource

from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import does_file_uri_exist


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


class Source(models.Model):

    MODE_L = (("geonet", "API de recherche GeoNetWork"),
              ("pdf", "Répertoire contenant des fichiers PDF"),
              ("wfs", "Service OGC:WFS"))

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uri = models.CharField("URI", max_length=2048)
    name = models.CharField("Name", max_length=250)
    mode = models.CharField("Mode", choices=MODE_L, default="pdf", max_length=250)

    # FK & alt
    user = models.ForeignKey(User)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__src = None

    def save(self, *args, **kwargs):

        if self.mode == 'pdf' and not does_file_uri_exist(str(self.uri)):
            raise Exception()  # TODO
        self.__src = OnegeoSource(self.uri, self.name, self.mode)

        super().save(*args, **kwargs)

    @property
    def src(self):
        return self.__src

    class Meta:
        verbose_name = "Source"
        unique_together = (("uri", "user"),)

    @property
    def s_uri(self):
        if self.mode == "pdf":
            dir_name = search("(\S+)/(\S+)", str(self.uri))
            return "file:///{}".format(dir_name.group(2))
        return self.uri

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @classmethod
    def get_from_uuid(cls, uuid, user=None):
        if user:
            sources = cls.objects.filter(user=user)
        else:
            sources = cls.objects.all()
        for src in sources:
            if str(src.uuid)[:len(uuid)] == uuid:
                return src
        return None

    @classmethod
    def custom_delete(cls, uuid, user):
        obj = cls.get_from_uuid(uuid)
        if not obj:
            data = {"error": "Echec de la suppression: Aucune source ne correspond à cet identifiant."}
            status = 404
        elif obj and obj.user == user:
            obj.delete()
            data = {}
            status = 204
        else:
            data = {"error": "Echec de la suppression: Vous n'etes pas l'usager de cette source."}
            status = 403
        return JsonResponse(data, status=status)

    @classmethod
    def custom_create(cls, request, uri, defaults):
        source, created = Source.objects.get_or_create(uri=uri, defaults=defaults)

        if created:
            response = JsonResponse(data={}, status=201)
            uri = request.build_absolute_uri()
            uri = uri.endswith('/') and uri[:-1] or uri
            response["Location"] = "{}/{}".format(uri, source.short_uuid)

        if created is False:
            data = {"error": "Echec de la création: L'élément est déjà existant."}
            response = JsonResponse(data=data, status=409)
        return response

    @classmethod
    def custom_create_old(cls, name, user, config):
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

    @property
    def format_data(self):
        return clean_my_obj({"id": self.short_uuid,
                             "uri": self.s_uri,
                             "mode": self.mode,
                             "name": self.name,
                             "location": "/sources/{}".format(self.short_uuid)})

    @classmethod
    def format_by_filter(cls, user):
        sources = cls.objects.filter(user=user).order_by("name")
        return [s.format_data for s in sources]


@receiver(post_save, sender=Source)
def on_save_source(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')

    def create_resources(instance, tsk):
        try:
            for res in instance.src.get_resources():
                resource = Resource.objects.create(
                    source=instance, name=res.name, columns=res.columns)
                resource.set_rsrc(res)
            tsk.success = True
            tsk.description = "Les ressources ont été créées avec succès. "
        except Exception as err:
            tsk.success = False
            tsk.description = str(err)  # TODO
        finally:
            tsk.stop_date = timezone.now()
            tsk.save()

    description = ("Création des ressources en cours. "
                   "Cette opération peut prendre plusieurs minutes. ")

    tsk = Task.objects.create(
        model_type="source", user=instance.user,
        model_type_id=instance.uuid, description=description)

    thread = Thread(target=create_resources, args=(instance, tsk))
    thread.start()
