# Copyright (c) 2017-2018 Neogeo-Technologies.
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
from django.contrib.auth import authenticate
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from functools import wraps
from re import search


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


def slash_remove(uri):  # TODO Supprimer la méthode
    return uri.endswith('/') and uri[:-1] or uri


def read_name(body_data):  # TODO Supprimer la méthode
    name = body_data.get("name", "")
    if name == "":
        return None
    try:
        name = search("^[a-z0-9_]{2,100}$", name)
        name = name.group(0)
    except AttributeError:
        return None
    return name
