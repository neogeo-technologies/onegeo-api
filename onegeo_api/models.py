from pathlib import Path
from re import search
from threading import Thread
import uuid
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.http import JsonResponse
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.shortcuts import get_object_or_404

from onegeo_manager.source import Source as OnegeoSource

from .elasticsearch_wrapper import elastic_conn


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


def clean_my_obj(obj):
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(clean_my_obj(x) for x in obj if x is not None)
    elif isinstance(obj, dict):
        return type(obj)((clean_my_obj(k), clean_my_obj(v))
                         for k, v in obj.items() if k is not None and v is not None)
    else:
        return obj


def does_file_uri_exist(uri):

    def retrieve(b):
        p = Path(b.startswith("file://") and b[7:] or b)
        if not p.exists():
            raise ConnectionError("Given path does not exist.")
        return [x.as_uri() for x in p.iterdir() if x.is_dir()]

    p = Path(uri.startswith("file://") and uri[7:] or uri)
    if not p.exists():
        return False
    if p.as_uri() in retrieve(PDF_BASE_DIR):
        return True


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
        all_src = Source.objects.all()
        for src in all_src:
            if str(src.uuid)[:len(uuid)] == uuid:
                if (user and src.user == user) or not user:
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


class Resource(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__rsrc = None

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250)
    columns = JSONField("Columns")

    # FK & alt
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Resource"

    @property
    def rsrc(self):
        return self.__rsrc

    def set_rsrc(self, rsrc):
        self.__rsrc = rsrc

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @property
    def format_data(self):
        d = {"id": self.short_uuid,
             "location": "/sources/{}/resources/{}".format(self.source.short_uuid, self.short_uuid),
             "name": self.name,
             "columns": self.columns}
        try:
            contexts = Context.objects.filter(resources=self)
        except Context.DoesNotExist:
            pass
        else:
            d.update(index=[ctx.format_data["location"] for ctx in contexts])
        finally:
            return clean_my_obj(d)

    @classmethod
    def get_from_uuid(cls, rsrc_uuid, user=None):

        all_rsrc = cls.objects.all()
        for rsrc in all_rsrc:
            if str(rsrc.uuid)[:len(rsrc_uuid)] == rsrc_uuid:
                if (user and rsrc.source.user == user) or not user:
                    return rsrc
        return None

    @classmethod
    def format_by_filter(cls, src_uuid, user):
        source = Source.get_from_uuid(uuid=src_uuid, user=user)
        rsrc = cls.objects.filter(source=source, source__user=user).order_by("name")
        return [r.format_data for r in rsrc]


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
    resources = models.ManyToManyField(Resource)

    def save(self, *args, **kwargs):
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
        all_ctx = cls.objects.all()
        for ctx in all_ctx:
            if str(ctx.uuid)[:len(uuid)] == uuid:
                for rsrc in ctx.resources:
                    if (user and rsrc.source.user == user) or not user:
                        return ctx
        return None

    @property
    def format_data(self):
        return {"location": "/indices/{}".format(self.short_uuid),
                "resource": ["/sources/{}/resources/{}".format(
                    r.source.short_uuid, r.short_uuid) for r in self.resources.all()],
                "columns": self.clmn_properties,
                "name": self.name,
                "reindex_frequency": self.reindex_frequency}

    @classmethod
    def format_by_filter(cls, user):
        contexts = Context.objects.filter(
            resources__in=Resource.objects.filter(source__user=user))
        return [ctx.format_data for ctx in contexts]


class SearchModel(models.Model):

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250, unique=True)
    config = JSONField("Config", blank=True, null=True)

    # FK & alt
    user = models.ForeignKey(User, blank=True, null=True)
    context = models.ManyToManyField(Context)

    def save(self, *args, **kwargs):
        set_names_ctx = Context.objects.all()
        for c in set_names_ctx:
            if self.name == c.name:
                raise ValidationError("Un modèle de recherche ne peut avoir "
                                      "le même nom qu'un contexte d'indexation.")
        super().save(*args, **kwargs)

    @property
    def short_uuid(self):

        return str(self.uuid)[:7]

    @property
    def format_data(self):
        def retreive_contexts(name):
            smc = SearchModel.context.through
            set = smc.objects.filter(searchmodel__name=name)
            return [s.context.name for s in set if s.context.name is not None]

        response = {
            "location": "profiles/{}".format(self.name),
            "name": self.name,
            "config": self.config,
            "indices": retreive_contexts(self.name)}

        contexts = [e.context for e in
                    SearchModel.context.through.objects.filter(searchmodel=self)]

        try:
            ext = import_module('..extensions.{0}'.format(self.name), __name__)
            response['extended'] = True
        except ImportError:
            ext = import_module('..extensions.__init__', __name__)
        finally:
            plugin = ext.plugin(self.config, contexts)
            if plugin.qs:
                response['qs_params'] = [{'key': e[0],
                                          'description': e[1],
                                          'type': e[2]} for e in plugin.qs]

        return clean_my_obj(response)

    @classmethod
    def get_from_user(cls, user):
        search_model = SearchModel.objects.filter(Q(user=user) | Q(user=None)).order_by("name")
        return [sm.format_data for sm in search_model]

    @classmethod
    def user_access(cls, name, model, user):
        sm = get_object_or_404(cls, name=name)
        if sm.user == user:
            return sm
        return None

    @classmethod
    def get_search_model(cls, name, user, config):
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


class Task(models.Model):
    T_L = (("source", "source"),
           ("context", "context"))

    start_date = models.DateTimeField("Start", auto_now_add=True)
    stop_date = models.DateTimeField("Stop", null=True, blank=True)
    success = models.NullBooleanField("Success")
    user = models.ForeignKey(User, blank=True, null=True)
    model_type = models.CharField("Model relation type", choices=T_L, max_length=250)
    model_type_id = models.CharField("Id model relation linked", max_length=250)
    description = models.CharField("Description", max_length=250)


# SIGNALS
# =======


@receiver(post_delete, sender=Context)
def on_delete_context(sender, instance, *args, **kwargs):
    Task.objects.filter(model_type_id=instance.pk, model_type="context").delete()
    elastic_conn.delete_index_by_alias(instance.name)


@receiver(post_save, sender=Source)
def on_save_source(sender, instance, *args, **kwargs):

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
