from functools import wraps
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse


class JsonError(Exception):

    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(message, status)


class MultiTaskError(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ContentTypeLookUp:

    def func_with_content_type(self, func, request, *args, **kwargs):
        if request.content_type != "application/json":
            data = {"error": "Le format demandé n'est pas pris en charge. "}
            return JsonResponse(data, status=406)
        else:
            return func(*args, **kwargs)

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            request = None
            args = list(args)
            for arg in args:
                if isinstance(arg, WSGIRequest):
                    request = arg

            return self.func_with_content_type(func, request, *args, **kwargs)

        return wrapper
