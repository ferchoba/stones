#!/usr/bin/env python
#-*- coding: utf-8 -*-

import logging
from webapp2_extras.appengine.auth.models import User as Webapp2_user

import stones


logger = logging.getLogger(__name__)


class User(Webapp2_user, stones.Expando):
  '''User model.'''
  created = stones.DateTimeProperty(auto_now_add=True)
  updated = stones.DateTimeProperty(auto_now=True)
  # ID for third party authentication, e.g. 'google:username'. UNIQUE.
  auth_ids = stones.StringProperty(repeated=True)
  # Hashed password. Not required because third party authentication
  # doesn't use password.
  password = stones.StringProperty()

  def _populate_from_dict(self, json):
    '''Populates the entity with data from dict.'''
    json.pop('password', None)
    super(User, self)._populate_from_dict(json)
