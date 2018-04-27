import csv
import datetime
from datetime import timezone
import dateutil.parser
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from collections import OrderedDict
# import logging
from onegeo_api.elasticsearch_wrapper import elastic_conn
from onegeo_api.models import Analyzer
from onegeo_api.models import Context
from onegeo_api.models import Filter
from onegeo_api.models import Task
from onegeo_manager.context import Context as OnegeoContext
from onegeo_manager.index import Index as OnegeoIndex
from onegeo_manager.resource import Resource as OnegeoResource
from onegeo_manager.source import Source as OnegeoSource
from uuid import uuid4
from onegeo_api.exceptions import ErrorLocked
import os.path

NOW = timezone.now()
TITRE_COLONNE = ["COLL_NOM", "COLL_SIRET", "BUDGET_ANNEE", "COL_COMMUNE",
                 "DELIB_NUM", "DELIB_DATE", "DELIB_OBJET", "PREF_ID",
                 "DELIB_URL"]


def iter_flt_from_anl(anl_name):
    AnalyserFilters = Analyzer.filter.through
    set = AnalyserFilters.objects.filter(analyzer__name=anl_name).order_by("id")
    return [s.filter.name for s in set if s.filter.name is not None]


class Command(BaseCommand):

    help = 'Update indexes'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        for instance in Context.objects.all():
            # if self.is_index_to_update(instance):
                self.update_index(instance)

    def is_index_to_update(self, instance):
        return {
            'never': None,
            'daily': True,
            'weekly': NOW.isoweekday() == 1,
            'monthly': NOW.day == 1,
            }.get(instance.reindex_frequency, None)

    def update_index(self, instance):

        last = Task.objects.filter(
            model_type='context',
            model_type_id=instance.pk).order_by('start_date').last()
        if last and last.success is None:
            raise ErrorLocked

        resource = instance.resource
        source = resource.source

        try:
            onegeo_source = OnegeoSource(source.uri, source.name, source.mode)
        except ConnectionError:
            raise Exception('La source de données est inaccessible.')

        onegeo_resource = OnegeoResource(onegeo_source, resource.name)
        for column in iter(resource.columns):
            if onegeo_resource.is_existing_column(column["name"]):
                continue
            onegeo_resource.add_column(
                column["name"], column_type=column["type"],
                occurs=tuple(column["occurs"]), count=column["count"],
                rule="rule" in column and column["rule"] or None)

        onegeo_index = OnegeoIndex(resource.name)
        onegeo_context = OnegeoContext(instance.name, onegeo_index, onegeo_resource)

        for col_property in iter(instance.clmn_properties):
            context_name = col_property.pop('name')
            onegeo_context.update_property(context_name, 'alias', col_property['alias'])
            onegeo_context.update_property(context_name, 'type', col_property['type'])
            onegeo_context.update_property(context_name, 'pattern', col_property['pattern'])
            onegeo_context.update_property(context_name, 'occurs', col_property['occurs'])
            onegeo_context.update_property(context_name, 'rejected', col_property['rejected'])
            onegeo_context.update_property(context_name, 'searchable', col_property['searchable'])
            onegeo_context.update_property(context_name, 'weight', col_property['weight'])
            onegeo_context.update_property(context_name, 'analyzer', col_property['analyzer'])
            onegeo_context.update_property(context_name, 'search_analyzer', col_property['search_analyzer'])

        opts = {}

        if source.mode == "pdf":
            pipeline = "attachment"
            elastic_conn.create_pipeline_if_not_exists(pipeline)
            opts.update({"pipeline": pipeline})

        opts.update({"collections": onegeo_context.get_collection()})

        body = {'mappings': onegeo_context.generate_elastic_mapping(),
                'settings': {
                    'analysis': self._retreive_analysis(
                        self._retreive_analyzers(onegeo_context))}}

        index_uuid = str(uuid4())[0:7]

        description = "Les données sont en cours d'indexation (id de l'index: '{0}'). ".format(
            index_uuid)
        task = Task.objects.create(model_type="context",
                                   description=description,
                                   model_type_id=instance.pk)

        def on_index_error(desc):
            pass

        def on_index_success(desc):
            task.success = True
            task.stop_date = timezone.now()
            task.description = desc
            task.save()

        def on_index_failure(desc):
            task.success = False
            task.stop_date = timezone.now()
            task.description = desc
            task.save()

        def dump_delib(document):
            '''
              Fonction permettant la generation d'un dump CSV tous les jours
              après l'intégration de nouveaux documents
            '''
            # chemin d'ecriture du fichier csv
            file_path = settings.DUMP_DELIB + 'delib_' + datetime.datetime.now().date().strftime('%Y%m%d')+'.csv'
            add_header = False
            if os.path.exists(file_path):
                add_header = True
            with open(file_path, 'a') as csvfile:
                writer = csv.writer(csvfile)
                # ecriture de l'entete du csv (titre des colonnes)
                if add_header is False:
                    writer.writerows([TITRE_COLONNE])
                try:
                    # URL absolue du pdf file: DELIB_URL
                    delib = False
                    # initialisation du dictionnaire
                    dic_row = OrderedDict.fromkeys(tuple(TITRE_COLONNE), None)
                    if document['origin']:
                        # verifier qu'on a bien des données de type delib
                        if type(document['origin']) is dict:
                            if 'resource' in document['origin']:
                                if type(document['origin']['resource']) is dict:
                                    if document['origin']['resource']['name'] == 'delib':
                                        delib = True
                                    else:
                                        delib = False
                            if delib == True and 'filename' in document['origin']:
                                uri = document['origin']['filename'].split("delib")
                                if len(uri) == 2:
                                    dic_row["DELIB_URL"] = settings.SERVICE_URL + uri[1]

                        if delib == True:
                            # valeur par defaut
                            dic_row["COLL_NOM"] = "Métropole de Lyon"
                            dic_row["COLL_SIRET"] = "20004697700019"
                            dic_row["PREF_ID"] = "Préfecture du Rhône"
                            # Date de reception du pdf
                            date_now = datetime.datetime.now(timezone.utc).isoformat()
                            date_now = dateutil.parser.parse(date_now)
                            dic_row["BUDGET_ANNEE"] = str(date_now.year)
                            # dic_row["PREF_DATE"] = str(date_now.year) + '-' + \
                            #     str(date_now.month) + '-' + str(date_now.day)
                            # champ properties du json
                            if document['properties']:
                                if type(document['properties']) is dict:
                                    # insertion des valeurs si elle existe
                                    # numero de sceance: DELIB_NUM
                                    if 'numero_seance' in document['properties']:
                                        dic_row["DELIB_NUM"] = document['properties']['numero_seance']
                                    # date sceance: DELIB_DATE
                                    if 'date_seance' in document['properties']:
                                        date_now = dateutil.parser.parse(document['properties']['date_seance'],dayfirst=True)
                                        dic_row["DELIB_DATE"] = str(date_now.year) + '-' + \
                                            str(date_now.month).zfill(2) + '-' + str(date_now.day).zfill(2)
                                    # titre:  DELIB_OBJET
                                    if 'titre' in document['properties']:
                                        dic_row["DELIB_OBJET"] = document['properties']['titre']
                                    # commune:  COL_COMMUNE
                                    if 'communes' in document['properties']:
                                        dic_row["COL_COMMUNE"] = document['properties']['communes']
                            # ecriture de la ligne
                            writer.writerows([dic_row.values()])
                except ValueError:
                    # logging.error("Erreur lors de la recuperation des donnees")
                    pass

        opts.update({"error": on_index_error,
                     "failed": on_index_failure,
                     "succeed": on_index_success,
                     "dump": dump_delib})

        elastic_conn.create_or_replace_index(
            index_uuid, instance.name, instance.name, body, **opts)

        return task.description

    def _retreive_analysis(self, analyzers):

        analysis = {'analyzer': {}, 'filter': {}, 'tokenizer': {}}

        for analyzer_name in analyzers:
            analyzer = Analyzer.objects.get(name=analyzer_name)

            plug_anal = analyzer.filter.through
            if analyzer.reserved:
                if plug_anal.objects.filter(analyzer__name=analyzer_name) and analyzer.tokenizer:
                    pass
                else:
                    continue

            if analyzer.config:
                analysis['analyzer'][analyzer.name] = analyzer.config
                continue

            analysis['analyzer'][analyzer.name] = {'type': 'custom'}

            tokenizer = analyzer.tokenizer

            if tokenizer:
                analysis['analyzer'][analyzer.name]['tokenizer'] = tokenizer.name
                if tokenizer.config:
                    analysis['tokenizer'][tokenizer.name] = tokenizer.config

            filters_name = iter_flt_from_anl(analyzer.name)

            for filter_name in iter(filters_name):
                filter = Filter.objects.get(name=filter_name)
                if filter.config:
                    analysis['filter'][filter.name] = filter.config

            analysis['analyzer'][analyzer.name]['filter'] = filters_name

        return analysis

    def _retreive_analyzers(self, context):

        analyzers = []
        for prop in context.iter_properties():
            if prop.analyzer not in analyzers:
                analyzers.append(prop.analyzer)
            if prop.search_analyzer not in analyzers:
                analyzers.append(prop.search_analyzer)
        return [analyzer for analyzer in analyzers if analyzer not in (None, '')]
