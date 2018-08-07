from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'samba4_manager:static')
    config.add_route('listar_usuarios', '/')
    config.add_route('listar_grupos','/grupos')
    config.add_route('listar_computadoras','/computadoras')
    config.add_route('agregar_usuario','/agregar_usuario')
    config.add_route('agregar_computadora','/agregar_computadora')
    config.add_route('editar_usuario_mostrar_form','/editar_usuario/{objectguid}')
    config.add_route('editar_usuario_grabar_form','/editar_usuario_grabar')
    config.add_route('editar_grupo_mostrar_form','/editar_grupo/{objectguid}')
    config.add_route('editar_grupo_grabar_form','/editar_grupo_grabar')
    config.add_route('editar_computadora_mostrar_form','/editar_computadora/{objectguid}')
    config.add_route('editar_computadora_grabar_form','/editar_computadora_grabar')
    config.add_route('listar_avanzado','/listar_avanzado')
    config.add_route('listar_subrama','/listar_subrama')
    config.scan()
    return config.make_wsgi_app()
