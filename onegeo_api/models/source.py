from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.utils import timezone
from re import search
from threading import Thread
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from onegeo_manager.source import Source as OnegeoSource

from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import does_file_uri_exist
from onegeo_api.models import AbstractModelProfile

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


class Source(AbstractModelProfile):

    MODE_L = (("geonet", "API de recherche GeoNetWork"),
              ("pdf", "Répertoire contenant des fichiers PDF"),
              ("wfs", "Service OGC:WFS"))

    mode = models.CharField("Mode", choices=MODE_L, default="pdf", max_length=250)
    uri = models.CharField("URI", max_length=2048)

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
        unique_together = (("uri", "user"), )

    @property
    def s_uri(self):
        if self.mode == "pdf":
            dir_name = search("(\S+)/(\S+)", str(self.uri))
            return "file:///{}".format(dir_name.group(2))
        return self.uri

    @property
    def detail_renderer(self):
        return clean_my_obj({"id": self.short_uuid,
                             "uri": self.s_uri,
                             "mode": self.mode,
                             "name": self.name,
                             "location": "/sources/{}".format(self.short_uuid)})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user).order_by("name")
        return [s.detail_renderer for s in instances]

    @classmethod
    def create_with_response(cls, request, uri, defaults):
        instance, created = cls.objects.get_or_create(uri=uri, defaults=defaults)

        if created:
            response = JsonResponse(data={}, status=201)
            uri = request.build_absolute_uri()
            uri = uri.endswith('/') and uri[:-1] or uri
            response["Location"] = "{}/{}".format(uri, instance.short_uuid)

        if created is False:
            data = {"error": "Echec de la création: La source est déjà existante."}
            response = JsonResponse(data=data, status=409)
        return response

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


@receiver(post_save, sender=Source)
def on_save_source(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')

    def create_resources(instance, tsk):
        try:
            for res in instance.src.get_resources():
                resource = Resource.objects.create(
                    source=instance, name=res.name,
                    columns=res.columns, user=instance.user)
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
