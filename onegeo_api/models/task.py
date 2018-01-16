from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.http import Http404

from onegeo_api.utils import clean_my_obj


class Task(models.Model):
    T_L = (("Source", "Source"),
           ("Context", "Context"))

    start_date = models.DateTimeField("Start", auto_now_add=True)
    stop_date = models.DateTimeField("Stop", null=True, blank=True)
    success = models.NullBooleanField("Success")
    model_type = models.CharField("Model relation type", choices=T_L, max_length=250)
    model_type_alias = models.CharField("Alias model relation", max_length=250, default=None)
    description = models.CharField("Description", max_length=250)

    # FK & alt
    user = models.ForeignKey(User)

    @property
    def detail_renderer(self):
        return clean_my_obj({
            "id": self.pk,
            "status": self.success is None and 'running' or 'done',
            "description": self.description,
            "location": "tasks/{}".format(self.pk),
            "success": self.success,
            "dates": {"start": self.start_date, "stop": self.stop_date}})

    @classmethod
    def list_renderer(cls, defaults):
        tasks = cls.objects.filter(Q(defaults=defaults) | Q(user=None)).order_by("-start_date")
        return [t.detail_renderer for t in tasks]

    @classmethod
    def get_with_permission(cls, defaults, user):
        try:
            instance = cls.objects.get(**defaults)
        except cls.DoesNotExist:
            raise Http404("Aucune tâche ne correspond à votre requête")
        if instance.user and instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette tâche")
        return instance
