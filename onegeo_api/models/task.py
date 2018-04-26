from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404
from django.utils import timezone
# from onegeo_api.celery_tasks import is_task_successful
import uuid


MODEL = 'onegeo_api'


class Task(models.Model):

    class Meta(object):
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    PATHNAME = '/tasks/{task}'

    DESCRIPTION_CHOICES = (
        ('0', 'Unkown'),
        ('1', 'Data source analyzing'),
        ('2', 'Indexing data'))

    alias = models.ForeignKey(
        to='Alias', verbose_name='Nickname', on_delete=models.CASCADE)

    celery_id = models.UUIDField(
        verbose_name='UUID', default=uuid.uuid4, editable=False)

    description = models.CharField(
        verbose_name='Description',
        choices=DESCRIPTION_CHOICES, max_length=1, default='0')

    start_date = models.DateTimeField(
        verbose_name='Start', auto_now_add=True)

    stop_date = models.DateTimeField(
        verbose_name='Stop', null=True, blank=True)

    success = models.NullBooleanField(verbose_name='Success')

    user = models.ForeignKey(to=User, verbose_name='User')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if self.celery_id and (self.start_date and not self.stop_date):
        #     self.success = is_task_successful(str(self.celery_id))

    @property
    def location(self):
        return self.PATHNAME.format(task=self.pk)

    @location.setter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self):

        elapsed_time = self.stop_date \
            and (self.stop_date - self.start_date) \
            or (timezone.now() - self.start_date)

        Model = apps.get_model(MODEL, self.alias.model_name)
        target = Model.objects.get(alias=self.alias)

        return {
            'dates': {
                'start': self.start_date,
                'end': self.stop_date},
            'type': self.get_description_display(),
            'elapsed_time': float('{0:.2f}'.format(elapsed_time.total_seconds())),
            'id': self.pk,
            'location': self.location,
            'status': {
                None: 'Running',
                False: 'Failed',
                True: 'Done'}.get(self.success),
            'target': target.location}

    @classmethod
    def list_renderer(cls, defaults):
        return [t.detail_renderer() for t in
                cls.objects.filter(**defaults).order_by('-start_date')]

    @classmethod
    def get_with_permission(cls, defaults, user):
        try:
            instance = cls.objects.get(**defaults)
        except cls.DoesNotExist:
            raise Http404()
        if instance.user and instance.user != user:
            raise PermissionDenied()
        return instance
