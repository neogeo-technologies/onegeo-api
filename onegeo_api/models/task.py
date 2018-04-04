from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404
from django.utils import timezone
import uuid


class Task(models.Model):

    class Meta(object):
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    DESCRIPTION = (
        ('0', 'ND'),
        ('1', 'Creation Source'),
        ('2', 'Creation Index ES')
    )

    alias = models.ForeignKey(
        to='Alias', verbose_name='Nickname', on_delete=models.CASCADE)
    name = models.CharField(
        verbose_name='Nom', max_length=250)

    celery_id = models.UUIDField(
        verbose_name='UUID', default=uuid.uuid4, editable=False)

    description = models.CharField(
                    verbose_name='Description', choices=DESCRIPTION,
                    max_length=1, default='0')

    start_date = models.DateTimeField(
        verbose_name='Start', auto_now_add=True)

    stop_date = models.DateTimeField(
        verbose_name='Stop', null=True, blank=True)

    success = models.NullBooleanField(verbose_name='Success')

    user = models.ForeignKey(to=User, verbose_name='User')

    @property
    def location(self):
        return '/tasks/{}'.format(self.pk)

    @location.setter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self):

        if self.stop_date:
            elapsed_time = (self.stop_date - self.start_date).total_seconds()
        else:
            elapsed_time = (timezone.now()-self.start_date).total_seconds()

        return {
            'id': self.pk,
            'alias': self.alias.handle,
            'name': self.name,
            'status': {
                None: 'running',
                False: 'failed',
                True: 'done'}.get(self.success),
            'description': self.get_description_display() +
            " (" + self.alias.handle+")",
            'location': self.location,
            'success': self.success,
            'elapsed_time': elapsed_time,
            'dates': {
                'start': self.start_date,
                'stop': self.stop_date}}

    @classmethod
    def list_renderer(cls, defaults):
        return [t.detail_renderer() for t in
                cls.objects.filter(**defaults).order_by('-start_date')]

    @classmethod
    def get_with_permission(cls, defaults, user):
        try:
            instance = cls.objects.get(**defaults)
        except cls.DoesNotExist:
            raise Http404('Aucune tâche ne correspond à votre requête')
        if instance.user and instance.user != user:
            raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette tâche")
        return instance
