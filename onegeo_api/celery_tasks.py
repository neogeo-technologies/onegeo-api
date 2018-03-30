from __future__ import absolute_import
from __future__ import unicode_literals
from celery.decorators import task
from celery.utils.log import get_task_logger
from django.apps import apps
from django.contrib.auth.models import User
from django.utils import timezone
from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.models import IndexProfile
from uuid import uuid4
logger = get_task_logger(__name__)


@task(name="create_resources_with_log", ignore_result=False)
def create_resources_with_log(**kwargs):

    # tache celery pour la creation des ressources d'une source

    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Source = apps.get_model(app_label='onegeo_api', model_name='Source')
    Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')

    source = Source.objects.get(pk=kwargs['pk'])
    task = Task.objects.get(celery_id=create_resources_with_log.request.id)

    try:
        for item in source.onegeo.get_resources():
            Resource.objects.create(**{
                'source': source, 'name': item.name,
                'columns': item.columns, 'user': source.user})
    except Exception as e:
        logger.error(e)
        task.success = False
    else:
        task.success = True
    finally:
        task.stop_date = timezone.now()
        task.save()


@task(name="create_es_index", ignore_result=False)
def create_es_index(**kwargs):

    # tache celery pour l'indexation des données dans ES

    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    user = User.objects.get(pk=kwargs['user'])
    index_profile = IndexProfile.get_or_raise(kwargs['nickname'], user)
    # index_profile = kwargs['index_profile']
    task = Task.objects.get(celery_id=create_es_index.request.id)

    try:
        for col_property in iter(index_profile.columns):
            # maj des prop des attributs (attr)
            name = col_property.pop('name')
            index_profile.onegeo.update_property(
                name, 'alias', col_property['alias'])
            index_profile.onegeo.update_property(
                name, 'type', col_property['type'])
            index_profile.onegeo.update_property(
                name, 'pattern', col_property['pattern'])
            index_profile.onegeo.update_property(
                name, 'occurs', col_property['occurs'])
            index_profile.onegeo.update_property(
                name, 'rejected', col_property['rejected'])
            index_profile.onegeo.update_property(
                name, 'searchable', col_property['searchable'])
            index_profile.onegeo.update_property(
                name, 'weight', col_property['weight'])
            index_profile.onegeo.update_property(
                name, 'analyzer', col_property['analyzer'])
            index_profile.onegeo.update_property(
                name, 'search_analyzer', col_property['search_analyzer'])
        # mapping pour ES
        mappings = index_profile.onegeo.generate_elastic_mapping()
        # creer ou mettre à jour l'index ES (par les alias)
        index = str(uuid4())
        # construction du setting (default pour le moment)
        body = {
            'mappings': {index: mappings.get("foo")},
            # 'settings': {}
            }
        # recuperation la collection de documents
        collection = index_profile.onegeo.get_collection()

        elastic_conn.create_index(index, body)
        # envoyer en masse les doc dans ES
        doc_type = index
        elastic_conn.push_collection(index, doc_type, collection)
        # mise à jours de l'alias
        es_alias = index_profile.alias.handle
        elastic_conn.switch_aliases(index, es_alias)
    except Exception as e:
        logger.error(e)
        task.success = False
    else:
        task.success = True
    finally:
        task.stop_date = timezone.now()
        task.save()
