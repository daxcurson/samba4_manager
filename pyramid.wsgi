from pyramid.paster import get_app, setup_logging
ini_path = '/mnt/c/dev-tools-and-data/web/proyectos/python/samba4_manager/production.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')
