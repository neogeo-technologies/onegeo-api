import functools
from base64 import b64decode
from pathlib import Path
from re import search

from .models import Source, Resource, Context, Filter, Analyzer, Tokenizer
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import IntegrityError
from django.db.models import Q


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


def format_resource(s, r):
    try:
        ctx = Context.objects.get(resource_id=r.id)
        d = {'id': r.id,
             'location': '/sources/{}/resources/{}'.format(s.id, r.id),
             'name': r.name,
             'columns': r.columns,
             'context': format_context(s, r, ctx)["location"]}
    except Context.DoesNotExist:
        d = {'id': r.id,
             'location': '/sources/{}/resources/{}'.format(s.id, r.id),
             'name': r.name,
             'columns': r.columns
             }
    return d


def format_source(s):
    d = {'id': s.id,
         'uri': s.s_uri,
         'mode': s.mode,
         'name': s.name,
         'location': '/sources/{}'.format(s.id),
         'resources': [format_resource(s, r) for r in list(Resource.objects.filter(source=s).order_by('name'))]}
    return d


def format_context(s, r, c):
    d = {"location": "/contexts/{}".format(c.resource_id),
         "resource": "/sources/{}/resources/{}".format(s.id, r.id),
         "columns": c.clmn_properties,
         "name": c.name,
         "reindex_frequency": c.reindex_frequency
    }
    return d


def format_filter(obj):
    return {
        "location": "filters/{}".format(obj.name),
        "name": obj.name,
        "config": obj.config,
        "reserved": obj.reserved}


def iter_flt_from_anl(anl_name):
    AnalyserFilters = Analyzer.filter.through
    set = AnalyserFilters.objects.filter(analyzer__name=anl_name).order_by('id')
    l=[]
    for s in set:
        l.append(s.filter.name)
    return l


def format_analyzer(obj):
    return {
        "location": "analyzers/{}".format(obj.name),
        "name": obj.name,
        "filters": iter_flt_from_anl(obj.name),
        "reserved": obj.reserved,
        "tokenizer": obj.tokenizer and obj.tokenizer.name or ""} 


def format_tokenizer(obj):
    return {
        "location": "tokenizers/{}".format(obj.name),
        "name": obj.name,
        "config": obj.config,
        "reserved": obj.reserved}

def get_sources(user):
    sources = Source.objects.filter(user=user).order_by('name')
    list = []
    for set in sources:
        list.append(format_source(set))
    return list


def get_sources_id(user, id):
    source = get_object_or_404(Source, id=id, user=user)
    return format_source(source)


def get_resources(user, src_id):
    source = Source.objects.get(id=src_id, user=user)
    rsrc = Resource.objects.filter(source=source, source__user=user).order_by('name')
    l = []
    for r in rsrc:
        l.append(format_resource(source, r))
    return l


def get_resources_id(user, src_id, rsrc_id):
    source = get_object_or_404(Source, id=src_id, user=user)
    rsrc = get_object_or_404(Resource, id=rsrc_id, source=source, source__user=user)
    return format_resource(source, rsrc)


def get_contexts(user):
    src = Source.objects.filter(user=user)
    l = []
    for s in src:
        rsrc = Resource.objects.filter(source=s, source__user=user)
        for r in rsrc:
            set = Context.objects.filter(resource_id=r.id, resource__source__user=user)
            for ctx in set:
                l.append(format_context(s, r, ctx))
    return l


def get_context_id(user, id):
    src = Source.objects.filter(user=user)
    l = []
    for s in src:
        rsrc = Resource.objects.filter(source=s, source__user=user)
        for r in rsrc:
            if r.id == id:
                ctx = Context.objects.get(resource_id=r.id, resource__source__user=user)
                return format_context(s, r, ctx)


def get_filters(user):
    flt = Filter.objects.filter(Q(user=user) | Q(user=None)).order_by('reserved', 'name')
    l = []
    for f in flt:
        l.append(format_filter(f))
    return l


def get_filter_id(user, name):
    l = None
    flt = get_object_or_404(Filter, name=name)
    if flt.user == user or flt.user is None:
        l = format_filter(flt)
    return l


def get_analyzers(user):
    l = []
    anl = Analyzer.objects.filter(Q(user=user) | Q(user=None)).order_by('reserved', 'name')
    for a in anl:
        l.append(format_analyzer(a))
    return l


def get_analyzers_id(user, name):
    l = None
    anl = get_object_or_404(Analyzer, name=name)
    if anl.user == user or anl.user is None:
        l = format_analyzer(anl)
    return l


def get_token(user):
    l = []
    tkn = Tokenizer.objects.filter(Q(user=user) | Q(user=None)).order_by('reserved', 'name')
    for t in tkn:
        l.append(format_tokenizer(t))
    return l


def get_token_id(user, name):
    l = None
    tkn = get_object_or_404(Tokenizer, name=name)
    if tkn.user == user or tkn.user is None:
        l = format_tokenizer(tkn)
    return l


def read_name(body_data):
    if "name" not in body_data or body_data["name"] == "":
        return None
    try:
        name = search("^\w{2,30}$", body_data["name"])
        name = name.group(0)
    except IntegrityError:
        return None
    return name


def uri_shortcut(b):
    """
    Retourne une liste d'uri sous la forme de "file:///dossier",
    afin de caché le chemin absolue des sources
    """
    p = Path(b.startswith("file://") and b[7:] or b)
    if not p.exists():
        raise ConnectionError('Given path does not exist.')
    l = []
    for x in p.iterdir():
        if x.is_dir():
            l.append('file:///{}'.format(x.name))
    return l


def check_uri(b):
    """
    Verifie si l'uri en param d'entrée recu sous la forme de "file:///dossier"
    Correspond a un des dossiers enfant du dossier parent PDF_BASE_DIR
    Retourne l'uri complete si correspondance, None sinon.
    NB: l'uri complete sera verifier avant tout action save() sur modele Source()
    """
    p = Path(PDF_BASE_DIR)
    if not p.exists():
        raise ConnectionError('Given path does not exist.')
    for x in p.iterdir():
        if x.is_dir() and x.name == b[8:]:
            return x.as_uri()
    return None


class HttpResponseUnauthorized(HttpResponse):
    """
        Surcharge HttpResponse pour retourner des erreur 401
    """
    status_code = 401


def basic_authenticate(fct):
    """USAGE views.py/functions:
        @utils.basic_authenticate
    """
    @functools.wraps(fct)  # Permet de transmettre les attributs
    def wrapper_fct(*args, **kwargs):
        if 'HTTP_AUTHORIZATION' in args[0].request.META:
            auth = args[0].request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = b64decode(auth[1]).decode("utf-8").split(':')
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        return fct(*args, **kwargs)
                    else:
                        return HttpResponseUnauthorized()

        response = HttpResponse()
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="%s"' % "Basic Auth Protected"
        return response

    return wrapper_fct


# Authentification clé api + droits liés
class UserAuthenticate:
    """USAGE views.py/functions:
        user = utils.get_user_or_401(request)
        if isinstance(user, HttpResponse):
            return user
        my_user= user()
    """

    def __init__(self, request):
        self.request = request

    def __enter__(self):
        if 'HTTP_AUTHORIZATION' in self.request.META:
            auth = self.request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = b64decode(auth[1]).decode("utf-8").split(':')
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        return User.objects.get(username=uname)
                    else:
                        return None

    def __call__(self, *args, **kwargs):
        with UserAuthenticate(self.request) as user:
            if not user:
                return None
            return user

    def __exit__(self, *args):
        pass

def get_user_or_401(request):
    user = UserAuthenticate(request)
    if user() is None:
        response = HttpResponse()
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="%s"' % "Basic Auth Protected"
        return response
    return user
