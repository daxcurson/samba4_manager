import os

from pyramid.paster import get_app, setup_logging

# Path to the .ini file; override it with the SAMBA4_MANAGER_INI environment variable.
ini_path = os.environ.get('SAMBA4_MANAGER_INI', '/etc/samba4_manager/production.ini')
setup_logging(ini_path)
application = get_app(ini_path, 'main')
