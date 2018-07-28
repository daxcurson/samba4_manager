from pyramid.paster import get_app, setup_logging
ini_path = '/var/www/html/samba4_manager/production.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')
