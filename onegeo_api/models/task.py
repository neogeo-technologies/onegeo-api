from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.http import Http404

class CeleryTask(models.Model):
    task_id = models.CharField(max_length = 150, unique=True)
    user = models.ForeignKey(User,blank=True, null=True)
    header_location = models.CharField(max_length = 150)
    status = models.CharField(max_length = 20, blank=True)

    def __str__(self):
        return '%s' % (self.user.username)

class Task(models.Model):
    T_L = (("Source", "Source"),
           ("IndexProfile", "IndexProfile"))

    start_date = models.DateTimeField("Start", auto_now_add=True)
    stop_date = models.DateTimeField("Stop", null=True, blank=True)
    success = models.NullBooleanField("Success")
    alias = models.OneToOneField("onegeo_api.Alias", on_delete=models.CASCADE)
    description = models.CharField("Description", max_length=250)

    # FK & alt
    user = models.ForeignKey(User)

    def detail_renderer(self):
        return {
            "id": self.pk,
            "status": self.success is None and 'running' or 'done',
            "description": self.description,
            "location": "tasks/{}".format(self.pk),
            "success": self.success,
            "dates": {
                "start": self.start_date,
                "stop": self.stop_date}}

    @classmethod
    def list_renderer(cls, defaults, **opts):
        tasks = cls.objects.filter(Q(**defaults) | Q(user=None)).order_by("-start_date")
        return [t.detail_renderer(**opts) for t in tasks]

    @classmethod
    def get_with_permission(cls, defaults, user):
        try:
            instance = cls.objects.get(**defaults)
        except cls.DoesNotExist:
            raise Http404("Aucune tâche ne correspond à votre requête")
        if instance.user and instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette tâche")
        return instance
