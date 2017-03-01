from pathlib import Path
from re import search

from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from onegeo_manager.source import PdfSource
# from onegeo_manager.index import Index
# from onegeo_manager.context import PdfContext

from .elasticsearch_wrapper import elastic_conn


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


def retrieve(b):
    p = Path(b.startswith("file://") and b[7:] or b)

    if not p.exists():
        raise ConnectionError('Given path does not exist.')

    return [x.as_uri() for x in p.iterdir() if x.is_dir()]


def does_uri_exist(uri):
    p = Path(uri.startswith("file://") and uri[7:] or uri)
    if not p.exists():
        return False
    if p.as_uri() in retrieve(PDF_BASE_DIR):
        return True


class Source(models.Model):

    MODE_L = (("pdf","pdf"),)
    user = models.ForeignKey(User)
    uri = models.CharField("URI", max_length=2048, unique=True)
    name = models.CharField("Name", max_length=250)
    mode = models.CharField("Mode", choices= MODE_L, default="pdf", max_length=250)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__src = None


    def save(self, *args, **kwargs):

        if not does_uri_exist(self.uri):
            raise Exception()  # TODO

        self.__src = PdfSource(self.uri, self.name, self.mode)

        super().save(*args, **kwargs)

    @property
    def src(self):
        return self.__src

    class Meta:
        verbose_name = "Source"
        unique_together = (('uri', 'user'),)

    @property
    def s_uri(self):
        dir_name = search('(\S+)\/(\S+)', self.uri)
        return 'file:///{}'.format(dir_name.group(2))


class Resource(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__rsrc = None

    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    name = models.CharField("Name", max_length=250)
    columns = JSONField("Columns")

    class Meta:
        verbose_name = "Resource"

    @property
    def rsrc(self):
        return self.__rsrc

    def set_rsrc(self, rsrc):
        self.__rsrc = rsrc


class Context(models.Model):
    RF_L = (
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("monthly", "monthly"),)

    resource = models.OneToOneField(Resource, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField("Name", max_length=250, unique=True)
    clmn_properties = JSONField("Columns")
    reindex_frequency = models.CharField("Reindex_frequency", choices=RF_L, default="monthly", max_length=250)


class Filter(models.Model):

    name = models.CharField("Name", max_length=250, unique=True, primary_key=True)
    user = models.ForeignKey(User)
    config = JSONField("Config", blank=True, null=True)


class Analyzer(models.Model):

    name = models.CharField("Name", max_length=250, unique=True, primary_key=True)
    user = models.ForeignKey(User)
    filter = models.ManyToManyField(Filter, blank=True)
    tokenizer = models.ForeignKey("Tokenizer", blank=True, null=True)


class Tokenizer(models.Model):

    name = models.CharField("Name", max_length=250, unique=True, primary_key=True)
    user = models.ForeignKey(User)
    config = JSONField("Config", blank=True, null=True)

# Signaux

@receiver(post_save, sender=Source)
def handler(sender, instance, *args, **kwargs):
    for res in instance.src.get_types():
        resource = Resource.objects.create(
                        source=instance, name=res.name, columns=res.columns)
        resource.set_rsrc(res)

@receiver(post_delete, sender=Context)
def handler(sender, instance, *args, **kwargs):
    elastic_conn.delete_index_by_alias(instance.name)  # easy
    

