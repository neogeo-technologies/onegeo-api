# Procédure d'installation

#### Installer les dépendances

```shell
> apt-get install python3.5-dev python3.5-venv
> apt-get install binutils
> apt-get install git
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
(onegeo_venv) /onegeo_venv> pip install --process-dependency-links --egg git+https://github.com/neogeo-technologies/onegeo-manager.git@0.0.1#egg=onegeo_manager-0.0.1
```

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
> vim /onegeo_venv/config/settings.py
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
    'django.contrib.sessions',
    'django.contrib.messages',
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

ES_VAR = {'HOST': 'elasticsearch', 'PORT': '80'}

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

PDF_DATA_BASE_DIR = '/path/to/data/pdf'

```

Puis :

```shell
> vim /onegeo_venv/config/urls.py
```

``` python
from django.conf.urls import include
from django.conf.urls import url
from django.contrib import admin


urlpatterns = [
    url('^admin/', admin.site.urls),
    url('^api/', include('onegeo_api.urls'))]

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

#### Charger les données par défaut en base

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) /onegeo_venv> python manage.py loaddata onegeo_api/data.json
```


#### Pour Apache (mode wsgi)

Ajouter dans la configuration du site `WSGIPassAuthorization on`




#### Mise en place de Celery pour les tâches asynchrones

Installation de Redis
```shell
 /onegeo_venv> brew install redis
 ```
 
Installation de Celery
 ```shell
 /onegeo_venv> pip install celery
 ```
 
Configuration de Celery
 
 Créer et Éditer le fichier config/celery.py avec le code python ci-dessous:
 
```shell
/onegeo_venv> vim /onegeo_venv/config/celery.py
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

Créer ou Éditer le fichier __init__.py (config/__init__.py):

```python
from __future__ import absolute_import
from .celery import app as celery_app  
```

Editer de nouveau le fichier settings.py (config/settings):

```python
CELERY_TASK_URL = 'XXXXXXXX' -> URL d'acces à One geo TODO!
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
```

#### Commande a lancé en local

Lancement de Redis:

```shell
/onegeo_venv> redis-server
```
[Optionnel] Test que Redis est bien lancé:

```shell
/onegeo_venv> redis-cli ping
```

Lancement du worker Celery:
```shell
/onegeo_venv> celery -A config worker --loglevel=info
```

 


