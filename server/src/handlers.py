#!/usr/bin/env python
#-*- coding: utf-8 -*-

import logging
import sys
import traceback

import webapp2
import webapp2_extras.jinja2
import webapp2_extras.sessions
import webapp2_extras.auth
import webapp2_extras.i18n
from webapp2_extras.i18n import gettext as _
from webapp2_extras.i18n import lazy_gettext as __

from google.appengine.ext import ndb
from google.appengine.api import users, namespace_manager, app_identity, mail

from .utils import *
import oauth2
from .oauth2 import get_service

from .model_handler_mixin import ModelHandlerMixin

__all__ = ['BaseHandler', 'ModelHandlerMixin', 'NoKeyError']
logger = logging.getLogger(__name__)


class Error(Exception):
    '''Error baseclass.'''


class NoKeyError(Error):
    '''No key to retrieve an entity.'''


class BaseHandler(webapp2.RequestHandler):
    """
        Base handler. Allows sessions, template rendering, locale support,
        error rendering and basic auth support.
    """
    # Whose users are allowed to access this resource
    # Empty array means all users: authorized and unauthorized
    # You can restrict by user type or user_id
    # TODO: We need dynamic users groups?
    # users_allowed = []
    users_allowed = [u'u']

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.auth_store = webapp2_extras.auth.get_store(app=self.app)

        # Dict to store errors
        self.errors = {}

    def log_errors(self):
        """Log errors"""
        url = self.request.route.build(self.request, self.request.route_args,
                                       self.request.route_kwargs)
        logger.error(u'Url:%s\nErrors: \n%s' % (url, self.errors))

    def render_errors(self, errors):
        """
            Render handlers errors.
        """
        self.errors.update(errors)
        self.log_errors()
        self.response.content_type = 'application/json'
        if not self.app.debug:
            del self.errors['Traceback']
        return self.response.write(
            webapp2_extras.json.encode(self.errors, ensure_ascii=False,
                                       cls=JSONEncoder)
        )

    def render_json(self, jsonable):
        '''Render JSON response'''
        self.response.content_type = 'application/json'
        self.response.write(
            webapp2_extras.json.encode(jsonable, ensure_ascii=False,
                                       cls=JSONEncoder)
        )

    def extract_json(self):
        '''Convert request body in JSON'''
        return webapp2_extras.json.decode(self.request.body)

    # Jinja2 support
    @webapp2.cached_property
    def jinja2(self):
        '''Returns a Jinja2 renderer cached in the app registry.'''
        return webapp2_extras.jinja2.get_jinja2(app=self.app)

    @property
    def base_url(self):
        '''Returns base url to the web application'''
        return self.request.host_url

    def render_response(self, _template, **_context):
        '''Renders a template and writes the result to the response.'''
        # default context to render response
        try:
            logout_url = webapp2.uri_for('signout')
        except:
            logout_url = users.create_logout_url('/')

        context = {
            'base_url': self.base_url,
            'dev': self.app.debug,
            'logout_url': logout_url,
            'user': self.user,
        }
        context.update(_context)
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)

    @webapp2.cached_property
    def user(self):
        '''Gets system user'''
        appengine_user = users.get_current_user()
        user_model = self.auth.store.user_model
        system_user = user_model.get_by_auth_id(
            u'google:' + appengine_user.email()
        )
        if not system_user:
            ok, system_user = user_model.create_user(
                u'google:' + appengine_user.email(),
                user_id=appengine_user.user_id(),
                nickname=appengine_user.nickname(),
                email=appengine_user.email(),
                type=['u'],
                projects=[]
            )
        return system_user

    def get_namespace(self):
        # return self.request.host
        # always return this to NSG project (legacy)
        return 'appspot.com'

    def set_namespace(self):
        '''Namespace for the request'''
        replace_map = [u':']
        namespace = self.get_namespace()
        for replace in replace_map:
            namespace = unicode(namespace).replace(replace, '.')
        self.namespace = namespace
        namespace_manager.set_namespace(self.namespace)

    def handle_exception(self, exception, debug):
        if getattr(exception, 'code', None):
            self.response.status = exception.code
        else:
            self.response.status = 500
        tb = sys.exc_info()[-1]
        ret = {
            'Error': exception.__class__.__name__,
            'Msg': unicode(exception),
            'Traceback': traceback.format_exc(tb),
        }
        return self.render_errors(ret)

    @ndb.toplevel
    def dispatch(self):
        # Set namespace
        self.set_namespace()

        # Get language to apply translations
        self.locale = self.request.headers.get('Accept-Language', 'es-ES')
        webapp2_extras.i18n.get_i18n().set_locale(self.locale)

        # Get a session store for this request.
        self.session_store = webapp2_extras.sessions.get_store(
            request=self.request
        )

        _dispatch = False
        if self.users_allowed:
            if self.user:
                for type in self.user.type:
                    _dispatch = _dispatch or type in self.users_allowed
                    if _dispatch:
                        break
                _dispatch = _dispatch or \
                    self.user.get_id() in self.users_allowed
        else:
            _dispatch = True

        if _dispatch:
            try:
                super(BaseHandler, self).dispatch()
            except:
                raise
            finally:
                # Save all sessions.
                self.session_store.save_sessions(self.response)
        else:
            redirect_to = webapp2.uri_for('signin', service_name='')
            come_back_to = self.request.route.build(
                self.request,
                self.request.route_args,
                self.request.route_kwargs
            )
            self.redirect(redirect_to + '?come_back_to=' + come_back_to)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session(backend='memcache')

    @webapp2.cached_property
    def auth(self):
        return webapp2_extras.auth.get_auth(request=self.request)


class SendMailHandler(webapp2.RequestHandler):
    '''Task manager to send emails.'''
    def get(self):
        sender = self.request.get('from')
        to = self.request.get('to')
        html = self.request.get('body_message')

        message = mail.EmailMessage(sender=sender)

        message.to = to
        message.body = html
        message.html = html

        message.send()

    post = get
