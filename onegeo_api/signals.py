from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
from django.utils import timezone

# from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.models import Analyzer
from onegeo_api.models import Filter
from onegeo_api.models import Tokenizer
from onegeo_api.models import Context
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source


#Ces connecteurs de signaux ont été enregistré dans les modules apps.py et __init__.py de l'application

@receiver(post_delete, sender=Analyzer)
@receiver(post_delete, sender=Context)
@receiver(post_delete, sender=Filter)
@receiver(post_delete, sender=Resource)
@receiver(post_delete, sender=SearchModel)
@receiver(post_delete, sender=Source)
@receiver(post_delete, sender=Tokenizer)
def delete_related_alias(sender, instance, **kwargs):
    if instance.alias:
        instance.alias.delete()


@receiver(post_save, sender=Source)
def on_post_save_source(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')

    def create_resources_with_log(instance, tsk):
        try:
            for res in instance.src.get_resources():
                # Le nom de la resource est utilisé en tant qu'alias,
                # à voir si on a besoin de faire autrement plus tard
                resource = Resource.custom_create(instance, res.name, res.columns, instance.user, res.name)
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
        model_type="Source", user=instance.user,
        model_type_alias=instance.alias.handle, description=description)
    create_resources_with_log(instance, tsk)
    # TODO: Mis en echec des test lors de l'utilisation de thread
    # thread = Thread(target=create_resources, args=(instance, tsk))
    # thread.start()


@receiver(post_delete, sender=Context)
def on_delete_context(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Task.objects.filter(model_type_alias=instance.alias.handle, model_type="Context").delete()
    # elastic_conn.delete_index_by_alias(instance.name) #Erreur sur l'attribut indices à None


@receiver(post_delete, sender=Source)
def on_delete_source(sender, instance, *args, **kwargs):
    Task = apps.get_model(app_label='onegeo_api', model_name='Task')
    Task.objects.filter(model_type_alias=instance.alias.handle, model_type="Source").delete()


@receiver(post_delete, sender=Resource)
def on_delete_resource(sender, instance, *args, **kwargs):
    if instance.context:
        instance.context.delete()
