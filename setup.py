import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid==2.0.2',
    'pyramid_chameleon==0.3',
    'pyramid_jinja2==2.8',
    'pyramid_debugtoolbar==4.9',
    'waitress==2.0.0',
    'secureconfig==0.2.0a0',
    'WTForms==2.3.3',
    'reconfigure==0.1.82'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
]

setup(
    name='samba4_manager',
    version='0.0',
    description='Samba4 Manager',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='Agustin Villafane',
    author_email='agusvillafane@yahoo.com.ar',
    url='https://github.com/daxcurson/samba4_manager',
    keywords='web pyramid pylons samba manager',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = samba4_manager:main',
        ],
    },
)
