#!/usr/bin/env python
#-*- coding: utf-8 -*-

import logging

import stones
import stones.oauth2 as oauth2

logger = logging.getLogger(__name__)


class AuthError(Exception):
  '''Error base class for module.'''


class ProviderConfNotFoundError(AuthError):
  '''Provider configuration not found in app settings.'''


class OAuth2Conf(stones.BaseHandler):
  '''Base class to handler that must be granted access to settings to find info
  about auth configuration.'''

  # Scope for actions.
  scope = ''

  def get_provider_conf(self, provider_name):
    '''Gets provider configuration.'''
    conf = self.app.config.load_config('stones.auth')
    if not conf:
      raise ProviderConfNotFoundError('No configuration found in settigs.')
    try:
      providers = conf['providers']
    except KeyError:
      raise ProviderConfNotFoundError(
        'No providers key found in Oauth2 settings.')
    try:
      provider = providers[provider_name]
    except KeyError:
      raise ProviderConfNotFoundError(
        'Provider "%s" not found in Oauth2 providers' % provider_name)
    return provider


class BaseOAuth2CallbackHandler(OAuth2Conf):
  '''Handler to handle Oauth2 request callback from provider.'''
  def get(self, provider=None):
    code = self.request.params.get('code', None)
    if not code:
      return self.redirect_to('oauth2.begin', provider=provider)

    oauth2_conf = self.get_provider_conf(provider)
    redirect_uri = self.uri_for('oauth2.callback', provider=provider,
                                _full=True)
    service = oauth2.get_service(provider)(redirect_uri=redirect_uri,
                                           **oauth2_conf)
    token = service.get_access_token(code)
    user_info = service.get_user_info(token)
    user_model = self.auth.store.user_model
    user = user_model.get_by_auth_id(':'.join([provider, user_info['email']]))
    user = self.auth.store.user_to_dict(user)
    if not user:
      # creates a new one
      user_info['type'] = ['u']
      ok, user = user_model.create_user(':'.join([provider, user_info['email']]),
                                        **user_info)
      if ok:
        user = user_model.get_by_auth_id(':'.join(
          [provider, user_info['email']]))
        user = self.auth.store.user_to_dict(user)
        self.auth.set_session(user)
        return self.redirect_to('home')
      else:
        raise AuthError('Username already taken.')
    else:
      self.auth.set_session(user)
      self.redirect_to('home')


class BaseOAuth2BeginHandler(OAuth2Conf):
  '''Handler to begin OAuth2 authentification process.'''
  def get(self, provider=None):
    oauth2_conf = self.get_provider_conf(provider)
    redirect_uri = self.uri_for('oauth2.callback', provider=provider,
                                _full=True)
    service = oauth2.get_service(provider)(redirect_uri=redirect_uri,
                                           **oauth2_conf)

    auth_url = service.get_authorization_url()
    return self.redirect(auth_url)


class BaseMakeSuperHeroHandler(OAuth2Conf):
  '''Handler to make one user super hero.'''
  users_allowed = ['u']
  def get(self):
    user_model = self.auth.store.user_model
    qry = user_model.query(user_model.type == 'superhero')
    superheros = qry.count()
    if superheros == 0:
      user_type = self.user.type
      user_type.append('superhero')
      self.user.type = user_type
      self.user.put()
      return self.redirect_to('home')
    raise AuthError('You have no honor! You cannot be a superhero!')
