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
(onegeo_venv) /onegeo_venv> pip install django==1.10
(onegeo_venv) /onegeo_venv> pip install --process-dependency-links git+https://github.com/neogeo-technologies/onegeo-manager.git@0.0.1#egg=onegeo_manager-0.0.1
(onegeo_venv) /onegeo_venv> pip install elasticsearch
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
> ln -s /apps/onegeo_api /onegeo_venv/
```

#### Initialiser Django

```shell
> cd /onegeo_venv
/onegeo_venv> source bin/activate
(onegeo_venv) django-admin startproject config .
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

ROOT_URLCONF = 'onegeo.urls'

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

WSGI_APPLICATION = 'onegeo.wsgi.application'

DATABASES = {
    'default': {
        'NAME': 'onegeo_api',
        'ENGINE': 'django.db.backends.postgresql',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST':  'localhost',
        'PORT': '5432'}}

ES_VAR = {'HOST': 'localhost', 'PORT': '80'}

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

PDF_DATA_BASE_DIR = '/path/to/dir/'

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
