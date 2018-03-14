from django.contrib.auth.models import User
from django.db import models
import datetime


class Dashboard(models.Model):

    task_id = models.CharField(max_length=150, unique=True)
    user = models.ForeignKey(User, blank=True, null=True)
    header_location = models.CharField(max_length=50)
    status = models.CharField(max_length=20, blank=True)
    date_creation = models.DateField(
        'Date', default=datetime.date.today,
        help_text="Date de creation de la tâche")

    def __str__(self):
        return '%s' % (self.user.username)

    def detail_renderer(self, **kwargs):
        return {
            'id': self.task_id,
            'status': self.status,
            'location': self.header_location,
            'username': self.user.username}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [item.detail_renderer(**opts) for item
                in cls.objects.filter(user=user).order_by('task_id')]
