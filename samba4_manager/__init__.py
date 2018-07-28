from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view(name='static', path='samba4_manager:static')
    config.add_route('listar_usuarios', '/')
    config.scan()
    return config.make_wsgi_app()
