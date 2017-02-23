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

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


def iter_src(s):
    d = {'id': s.id,
         'uri': s.s_uri,
         'location': '/sources/{}'.format(s.id),
         'resources': [{'id': r.id,
                        'name': r.name,
                        'location': '/sources/{}/resources/{}'.format(s.id, r.id),
                        'columns': r.columns} for r in list(Resource.objects.filter(source=s))]}
    return d


def iter_rsrc(s, r):
    try:
        ctx = Context.objects.get(resource_id=r.id)
        d = {'id': r.id,
             'location': '/sources/{}/resources/{}'.format(s.id, r.id),
             'name': r.name,
             'columns': r.columns,
             'context': iter_ctx(s, r, ctx)["location"]}
    except Context.DoesNotExist:
        d = {'id': r.id,
             'location': '/sources/{}/resources/{}'.format(s.id, r.id),
             'name': r.name,
             'columns': r.columns
             }
    return d


def iter_ctx(s, r, c):
    d = {"location": "/contexts/{}".format(c.resource_id),
         "resource": "/sources/{}/resources/{}".format(s.id, r.id),
         "columns": c.clmn_properties,
         "name": c.name
    }
    return d


def iter_flt(f):
    d = {"location": "filters/{}".format(f.name),
         "name": f.name,
         "config": f.config
    }
    return d


def iter_flt_from_anl(anl_name):
    AnalyserFilters = Analyzer.filter.through
    set = AnalyserFilters.objects.filter(analyzer__name=anl_name)
    l=[]
    for s in set:
        l.append(s.filter.name)
    return l


def iter_anl(a):
    d = {'location':'analyzers/{}'.format(a.name),
         'name': a.name,
         'filters': iter_flt_from_anl(a.name),
         'tokenizer': a.tokenizer and a.tokenizer.name or ""
    }
    return d


def iter_tkn(t):
    d = {"location": "tokenizers/{}".format(t.name),
         "name": t.name,
         "config": t.config
         }
    return d

def get_sources(user):
    sources = Source.objects.filter(user=user)
    list = []
    for set in sources:
        list.append(iter_src(set))
    return list


def get_sources_id(user, id):
    source = get_object_or_404(Source, id=id, user=user)
    return iter_src(source)


def get_resources(user, src_id):
    source = Source.objects.get(id=src_id, user=user)
    rsrc = Resource.objects.filter(source=source, source__user=user)
    list = []
    for r in rsrc:
        list.append(iter_rsrc(source, r))
    return list


def get_resources_id(user, src_id, rsrc_id):
    source = get_object_or_404(Source, id=src_id, user=user)
    rsrc = get_object_or_404(Resource, id=rsrc_id, source=source, source__user=user)
    return iter_rsrc(source, rsrc)


def get_contexts(user):
    src = Source.objects.filter(user=user)
    l = []
    for s in src:
        rsrc = Resource.objects.filter(source=s, source__user=user)
        for r in rsrc:
            set = Context.objects.filter(resource_id=r.id, resource__source__user=user)
            for ctx in set:
                l.append(iter_ctx(s, r, ctx))
    return l


def get_context_id(user, id):
    src = Source.objects.filter(user=user)
    l = []
    for s in src:
        rsrc = Resource.objects.filter(source=s, source__user=user)
        for r in rsrc:
            if r.id == id:
                ctx = Context.objects.get(resource_id=r.id, resource__source__user=user)
                return iter_ctx(s, r, ctx)



def get_filters(user):
    flt = Filter.objects.filter(user=user)
    l = []
    for f in flt:
        l.append(iter_flt(f))
    return l


def get_filter_id(user, name):
    flt = get_object_or_404(Filter, user=user, name=name)
    return iter_flt(flt)


def get_analyzers(user):
    anl = Analyzer.objects.filter(user=user)
    l = []
    for a in anl:
        l.append(iter_anl(a))
    return l


def get_analyzers_id(user, name):
    anl = get_object_or_404(Analyzer, user=user, name=name)
    return iter_anl(anl)

def get_token(user):
    tkn = Tokenizer.objects.filter(user=user)
    l = []
    for t in tkn:
        l.append(iter_tkn(t))
    return l


def get_token_id(user, name):
    tkn = get_object_or_404(Tokenizer, user=user, name=name)
    return iter_tkn(tkn)


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
            print(x.name)
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