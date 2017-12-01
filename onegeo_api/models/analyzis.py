from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.http import Http404
import uuid

from onegeo_api.utils import clean_my_obj


class AbstractAnalyzis(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=250, unique=True)
    user = models.ForeignKey(User, blank=True, null=True)
    config = JSONField("Config", blank=True, null=True)
    reserved = models.BooleanField("Reserved", default=False)

    class Meta:
        abstract = True

    def __unicode__(self):
            return self.name

    @property
    def format_data(self):
        return clean_my_obj({"location": "{}/{}".format(self.namespace, self.name),
                             "name": self.name,
                             "config": self.config or None,
                             "reserved": self.reserved})

    @property
    def short_uuid(self):
        return str(self.uuid)[:7]

    @classmethod
    def get_from_uuid(cls, uuid, user=None):
        if user:
            instances = cls.objects.filter(user=user)
        else:
            instances = cls.objects.all()
        for obj in instances:
            if str(obj.uuid)[:len(uuid)] == uuid:
                return obj
        return None

    @classmethod
    def custom_filter(cls, user):
        instances = cls.objects.filter(Q(user=user) | Q(user=None)).order_by("reserved", "name")
        return [obj.format_data for obj in instances]

    @classmethod
    def custom_get_object_or_404(cls, uuid):
        instances = cls.objects.all()
        for obj in instances:
            if str(obj.uuid)[:len(uuid)] == uuid:
                return obj
        raise Http404

    @classmethod
    def user_access(cls, uuid, user):
        instance = cls.custom_get_object_or_404(uuid=uuid)
        if instance.user != user:
            raise PermissionDenied
        return instance


class RelatedFilters(models.Model):
    analyzer = models.ForeignKey("Analyzer")
    filter = models.ForeignKey("Filter")


class Analyzer(AbstractAnalyzis):

    filters = models.ManyToManyField("Filter", through="RelatedFilters", blank=True)
    tokenizer = models.ForeignKey("Tokenizer", blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.namespace = "analyzers"

    @property
    def format_data(self):
        filt_names = [f.name for f in self.filters.all().order_by("name")]

        return clean_my_obj({
            "location": "analyzers/{}".format(self.namespace, self.name),
            "name": self.name,
            "config": self.config or None,
            "tokenfilters": filt_names or None,
            "reserved": self.reserved,
            "tokenizer": self.tokenizer and self.tokenizer.name or None})


class Filter(AbstractAnalyzis):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.namespace = "tokenfilters"

    # @property
    # def format_data(self):
    #     return clean_my_obj({"location": "{}/{}".format(self.namespace, self.name),
    #                          "name": self.name,
    #                          "config": self.config or None,
    #                          "reserved": self.reserved})


class Tokenizer(AbstractAnalyzis):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.namespace = "tokenizers"

    # @property
    # def format_data(self):
    #     return clean_my_obj({"location": "{}/{}".format(self.namespace, self.name),
    #                          "name": self.name,
    #                          "config": self.config or None,
    #                          "reserved": self.reserved})
