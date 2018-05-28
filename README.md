# Procédure d'installation

#### Installer les dépendances

```shell
> apt-get install python3.5-dev python3.5-venv
> apt-get install binutils
> apt-get install git
> apt-get install redis
```

#### Mettre en place l'environnement virtuel Python 3.5

```shell
> cd /
/> mkdir onegeo_venv
/> cd onegeo_venv
/onegeo_venv> pyvenv-3.5 ./
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> pip install --upgrade pip
(onegeo_venv) /onegeo_venv> pip install --upgrade setuptools
(onegeo_venv) /onegeo_venv> pip install psycopg2
(onegeo_venv) /onegeo_venv> pip install 'django>=1.10,<1.11'
(onegeo_venv) /onegeo_venv> pip install 'elasticsearch>=5.0.0,<6.0.0'
(onegeo_venv) /onegeo_venv> pip install PyPDF2
(onegeo_venv) /onegeo_venv> pip install redis
(onegeo_venv) /onegeo_venv> pip install celery
(onegeo_venv) /onegeo_venv> pip install --process-dependency-links git+https://github.com/neogeo-technologies/onegeo-manager.git@nightly#egg=onegeo_manager
```

#### Lancer Redis

Utilisez pour cela la commande `redis-server`.

#### Récupérer les codes sources

```shell
> cd /
/> mkdir apps
/> cd apps
/apps> git clone https://github.com/neogeo-technologies/onegeo_api.git
```
Puis

```shell
> ln -s /apps/onegeo-api/onegeo_api/ /onegeo_venv/
```

#### Initialiser Django

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> django-admin startproject config .
```

#### Éditer les fichiers de configuration Django

D'abord :

```shell
> vi /onegeo_venv/config/settings.py
```

```python
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz0123456789'

DEBUG = False

ALLOWED_HOSTS = ['localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'onegeo_api']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware']

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages']}}]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'NAME': 'onegeo_api',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST':  'localhost',
        'PORT': '5432'}}

ELASTICSEARCH_HOSTS = [
    {'host': 'localhost', 'port': '9200', 'timeout': 10}]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/html/static/'

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

PDF_DATA_BASE_DIR = '/path/to/data/pdf'  # optionnel

SITE_ID = 1

API_BASE_PATH = 'api/'

```

Ensuite :

```shell
> vi /onegeo_venv/config/urls.py
```

```python
from django.conf.urls import include
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin


API_BASE_PATH = settings.API_BASE_PATH


urlpatterns = [
    url('^admin/', admin.site.urls),
    url('^{}'.format(API_BASE_PATH), include('onegeo_api.urls', namespace='onegeo-api'))]

```

Ainsi que :

```shell
> vi /onegeo_venv/config/celery.py
```

```python
import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
```

Et :

```shell
> vi /onegeo_venv/config/__init__.py
```

```python
from __future__ import absolute_import
from .celery import app as celery_app
```


#### Maintenant lancer le worker __Celery__

```shell
(onegeo_venv) /onegeo_venv> celery -A config worker --loglevel=info
```

#### Vérifier l'installation

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> python manage.py check
```

#### Déployer les bases de données

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> python manage.py migrate
```

#### Créer le super utilisateur Django

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> python manage.py createsuperuser
```

#### Déployer les fichiers `static`

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> python manage.py collectstatic
```


#### Pour Apache (mode wsgi)

Ajouter dans la configuration du site `WSGIPassAuthorization on`
