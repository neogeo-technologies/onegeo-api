import os
from setuptools import setup


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='onegeo-api',
    version='0.0.1',
    packages=['onegeo_api'],
    include_package_data=True,
    license='GNU GENERAL PUBLIC LICENSE',
    description="API d'administration de Onegeo",
    url='https://github.com/neogeo-technologies/onegeo-api',
    author='Neogeo Technologies',
    author_email='contact@neogeo.fr',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'],
    install_requires=[
        'elasticsearch>=5.5.0',
        'PyPDF2>=1.26.0',
        'onegeo-manager==0.0.1'],
    dependency_links=[
        'git+https://github.com/neogeo-technologies/onegeo-manager.git@0.0.1#egg=onegeo-manager-0.0.1'])
