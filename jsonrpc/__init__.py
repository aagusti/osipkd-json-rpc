import locale
import datetime
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import has_permission
from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.interfaces import IRoutesMapper
from pyramid.httpexceptions import (
    default_exceptionresponse_view,
    HTTPFound,
    )

from sqlalchemy import engine_from_config

from .security import group_finder, get_user
from .models import (
    DBSession,
    PbbDBSession,
    Base,
    PbbBase,
    init_model,
    )
from .tools import DefaultTimeZone

from pyramid.renderers import JSON

# http://stackoverflow.com/questions/9845669/pyramid-inverse-to-add-notfound-viewappend-slash-true    
class RemoveSlashNotFoundViewFactory(object):
    def __init__(self, notfound_view=None):
        if notfound_view is None:
            notfound_view = default_exceptionresponse_view
        self.notfound_view = notfound_view

    def __call__(self, context, request):
        if not isinstance(context, Exception):
            # backwards compat for an append_notslash_view registered via
            # config.set_notfound_view instead of as a proper exception view
            context = getattr(request, 'exception', None) or context
        path = request.path
        registry = request.registry
        mapper = registry.queryUtility(IRoutesMapper)
        if mapper is not None and path.endswith('/'):
            noslash_path = path.rstrip('/')
            for route in mapper.get_routes():
                if route.match(noslash_path) is not None:
                    qs = request.query_string
                    if qs:
                        noslash_path += '?' + qs
                    return HTTPFound(location=noslash_path)
        return self.notfound_view(context, request)
    
    
# https://groups.google.com/forum/#!topic/pylons-discuss/QIj4G82j04c
def url_has_permission(request, permission):
    return has_permission(permission, request.context, request)

@subscriber(BeforeRender)
def add_global(event):
     event['permission'] = url_has_permission

def get_title(request):
    route_name = request.matched_route.name
    return titles[route_name]

routes = [    
    ('home', '/', 'Home'),
    ('login', '/login', 'Login'),
    ('logout', '/logout', None),
    ('password', '/password', 'Change password'),
    ('user', '/user', 'Users'),
    ('user-add', '/user/add', 'Add user'),
    ('user-edit', '/user/{id}/edit', 'Edit user'),
    ('user-delete', '/user/{id}/delete', 'Delete user'),    
    ]

main_title = 'JSON-RPC'

titles = {}
for name, path, title in routes:
    if title:
        titles[name] = ' - '.join([main_title, title])
    
    
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    if settings['bphtb_sqlalchemy.url']:
        bphtb_engine = engine_from_config(settings, 'bphtb_sqlalchemy.')
        BphtbDBSession.configure(bind=bphtb_engine)        
        BphtbBase.metadata.bind = bphtb_engine
        
    if settings['pbb_sqlalchemy.url']:
        pbb_engine = engine_from_config(settings, 'pbb_sqlalchemy.')
        PbbDBSession.configure(bind=pbb_engine)        
        PbbBase.metadata.bind = pbb_engine
        
    if settings['padl_sqlalchemy.url']:
        padl_engine = engine_from_config(settings, 'padl_sqlalchemy.')
        PadlDBSession.configure(bind=padl_engine)
        PadlBase.metadata.bind = padl_engine 
        
    init_model()
    
    json_renderer = JSON()
    json_renderer.add_adapter(datetime.datetime, lambda v: v.isoformat())

    session_factory = session_factory_from_settings(settings)
    if 'localization' not in settings:
        settings['localization'] = 'id_ID.UTF-8'
    locale.setlocale(locale.LC_ALL, settings['localization'])        
    if 'timezone' not in settings:
        settings['timezone'] = DefaultTimeZone
    config = Configurator(settings=settings,
                          root_factory='jsonrpc.models.RootFactory',
                          session_factory=session_factory)
    config.include('pyramid_beaker')                          
    config.include('pyramid_chameleon')

    config.include('pyramid_rpc.jsonrpc')
    config.add_renderer('json', json_renderer)
    
    authn_policy = AuthTktAuthenticationPolicy('sosecret',
                    callback=group_finder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()                          
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.add_request_method(get_user, 'user', reify=True)
    config.add_request_method(get_title, 'title', reify=True)
    config.add_notfound_view(RemoveSlashNotFoundViewFactory())        
                          
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('deform_static', 'deform:static')
    
    
    for name, path, title in routes:
        config.add_route(name, path)
        
    config.add_jsonrpc_endpoint('pbb', '/pbb', default_renderer="json")
    config.add_jsonrpc_endpoint('bphtb', '/bphtb')
    config.add_jsonrpc_endpoint('padl', '/padl')
    
    config.scan()
    return config.make_wsgi_app()
