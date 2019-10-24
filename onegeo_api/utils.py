# Copyright (c) 2017-2019 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from base64 import b64decode
from collections import deque
from collections import Mapping
from django.contrib.auth import authenticate
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from functools import wraps
from numbers import Number
from onegeo_api.exceptions import ConflictError
from pathlib import Path
import sys


class HttpResponseSeeOther(HttpResponseRedirect):
    status_code = 303


class BasicAuth(object):

    def view_or_basicauth(self, view, request, test_func, *args, **kwargs):
        http_auth = request.META.get('HTTP_AUTHORIZATION', '')
        if http_auth not in ('', None):
            auth = http_auth.split()
            if len(auth) == 2:
                if auth[0].lower() == 'basic':
                    try:
                        username, password = b64decode(
                            auth[1]).decode('utf-8').split(':')
                    except Exception:
                        pass
                    user = authenticate(username=username, password=password)
                    if user is not None and user.is_active:
                        request.user = user
                        return view(*args, **kwargs)

        return HttpResponse(status=401)

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            request = None
            args = list(args)
            for arg in args:
                if isinstance(arg, WSGIRequest):
                    request = arg
                    break
            return self.view_or_basicauth(
                f, request, lambda u: u.is_authenticated(), *args, **kwargs)

        return wrapper


class Singleton(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)
        return cls.__instances[cls]


def clean_my_obj(obj):
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(clean_my_obj(x) for x in obj if x is not None)
    elif isinstance(obj, dict):
        return type(obj)(
            (clean_my_obj(k), clean_my_obj(v))
            for k, v in obj.items() if k is not None and v is not None)
    else:
        return obj


def merge_two_objs(obj1, obj2, path=None):
    """Merge 'obj1' to 'obj2'."""
    if path is None:
        path = []
    for k in obj2:
        if k in obj1:
            if isinstance(obj1[k], dict) and isinstance(obj2[k], dict):
                merge_two_objs(obj1[k], obj2[k], path + [str(k)])
            elif obj1[k] == obj2[k]:
                pass
            else:
                if isinstance(obj2[k], str):
                    desc = "value '{}' is ambiguous".format(obj2[k])
                else:
                    desc = "values {} are ambiguous".format(
                        ', '.join(["'{}'".format(v) for v
                                   in (set(obj2[k]) - set(obj1[k]))]))

                raise ConflictError(
                    "Conflict error at path: '{0}.{1}': {2}".format(
                        '.'.join(path), str(k), desc))
        else:
            obj1[k] = obj2[k]
    return obj1


def subdirectories(root):
    p = Path(root)
    if not p.exists():
        raise ConnectionError('Given path does not exist.')
    return [x.as_uri() for x in p.iterdir() if x.is_dir()]


def estimate_size(obj):
    """Recursively iterate to sum size of object."""
    done = []

    def inner(sub):
        if id(sub) in done:
            return 0

        sizeof = sys.getsizeof(sub)
        if isinstance(sub, (str, bytes, Number, range, bytearray)):
            pass  # bypass remaining control flow and return
        elif isinstance(sub, (tuple, list, set, deque)):
            sizeof += sum(inner(i) for i in sub)
        elif isinstance(sub, Mapping) or hasattr(sub, 'items'):
            sizeof += sum(inner(k) + inner(v) for k, v in getattr(sub, 'items')())

        # Check for custom object instances - may subclass above too
        if hasattr(sub, '__dict__'):
            sizeof += inner(vars(sub))
        if hasattr(sub, '__slots__'):  # can have __slots__ with __dict__
            sizeof += sum(inner(getattr(sub, s)) for s in sub.__slots__ if hasattr(sub, s))

        done.append(id(obj))
        return sizeof

    return inner(obj)


def pagination_handler(f):

    @wraps(f)
    def wrapper(*args, **kwargs):
        x = kwargs.pop('page_number', None)
        y = kwargs.pop('page_size', None)
        if isinstance(x, int) and isinstance(y, int) and x > 0 and y > 0:
            i = (x * y) - y
            j = i + y
            kwargs.update({'i': i, 'j': j})

        return f(*args, **kwargs)
    return wrapper
