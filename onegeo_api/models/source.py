from django.db import models
from django.http import JsonResponse
from django.http import Http404
from django.core.exceptions import PermissionDenied

from re import search

from onegeo_manager.source import Source as OnegeoSource

from onegeo_api.utils import clean_my_obj
from onegeo_api.utils import does_file_uri_exist
from onegeo_api.models.abstracts import AbstractModelProfile


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
        kwargs['model_name'] = 'Source'

        if self.mode == 'pdf' and not does_file_uri_exist(str(self.uri)):
            raise Exception()  # TODO
        self.__src = OnegeoSource(self.uri, self.name, self.mode)
        return super().save(*args, **kwargs)

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
        return clean_my_obj({"uri": self.s_uri,
                             "mode": self.mode,
                             "name": self.name,
                             "alias": self.alias.handle,
                             "location": "/sources/{}".format(self.alias.handle)})

    @classmethod
    def list_renderer(cls, user):
        instances = cls.objects.filter(user=user).order_by("name")
        return [s.detail_renderer for s in instances]

    @classmethod
    def create_with_response(cls, request, defaults):
        instance = cls.objects.create(**defaults)

        response = JsonResponse(data={}, status=201)
        uri = request.build_absolute_uri()
        uri = uri.endswith('/') and uri[:-1] or uri
        response["Location"] = "{}/{}".format(uri, instance.alias.handle)

        return response

    @classmethod
    def get_with_permission(cls, alias, user):
        try:
            instance = cls.objects.get(alias__handle=alias)
        except cls.DoesNotExist:
            raise Http404("Aucune source ne correspond à votre requete. ")
        if instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette source")
        return instance
