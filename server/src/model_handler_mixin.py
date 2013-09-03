#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of Stones Server Side.

# Stones Server Side is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Stones Server Side is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Stones Server Side.  If not, see <http://www.gnu.org/licenses/>.

# Copyright 2013, Carlos León <carlos.eduardo.leon.franco@gmail.com>

import logging

import webapp2_extras
from .model import Key

from google.appengine.ext import ndb

from .utils import *

from google.appengine.ext.ndb import Property


logger = logging.getLogger(__name__)


from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError


class Error(Exception):
  '''Base class to errors'''


class NoKeyOrIdError(Error):
  '''Occurs when no key or id is provided to find a single entity.'''


class NoEntityError(Error):
  '''Occurs when is imposible to find an entity.'''


def get_entity_by_key(key):
  '''Retrieves an entity by a key.'''
  try:
    entity = Key(urlsafe=key).get()
    if not entity:
      raise NoEntityError
    return entity
  except ProtocolBufferDecodeError, e:
    raise NoEntityError


class ModelHandlerMixin(object):
  '''
    Mixin to add model CRUD to handler.
  '''
  # our model class
  model = None
  # properties to sort GET responses
  # it should be model properties, e.g., MyModel.myproperty
  ordering = []
  # model properties to be retrieved in GET responses
  # it should be strings, e.g., 'myproperty'
  GET_properties = []

  def _pre_get_hook(self):
    '''To run before GET.'''

  def _post_get_hook(self, result):
    '''To run after GET.
    result: Array with found entities to be returned.'''
    return result

  def build_filters(self, kwargs):
    '''Builds filters to retrieve entities.'''
    params = kwargs.copy()
    params.update(self.request.params)

    qry_params = []
    for param_key, param_value in params.iteritems():
      if param_value:
        try:
          attr = getattr(self.model, param_key)
          qry_params.append(attr == attr._set_from_dict(param_value))
        except:
          # i don't take care about non _set_from_dict properties and
          # inexistent model properties
          pass

    return qry_params

  def build_order(self):
    '''Builds entities sorting.'''
    rv = []
    for order in self.ordering:
      if not isinstance(order, Property):
        continue

      rv.append(order)
    return rv

  def get(self, **kwargs):
    '''GET verb.
    Returns a list of entities, even if the result is a single entity.

    We assume 'key' or 'id' for identify one entity through url param.'''

    @ndb.tasklet
    def get_entities(qry):
      _entities = yield qry.fetch_async()
      raise ndb.Return(_entities)

    self._pre_get_hook()
    key = kwargs.pop('key', None) or self.request.get('key')
    id = kwargs.get('id', None) or self.request.get('id')
    if key:
      try:
        entities = get_entity_by_key(key)
      except NoEntityError:
        return self.abort(404, '%s not found.' % self.model.__class__.__name__)
    elif id:
      entities = self.model.get_by_id(id)
      if not entities:
        return self.abort(404, '%s not found.' % self.model.__class__.__name__)
    else:
        # No key or id. We need to return entities by query filters.
        filters = self.build_filters(kwargs)
        order = self.build_order()
        qry = self.model.query(*filters).order(*order)
        entities = get_entities(qry).get_result()

    entities = self._post_get_hook(entities)

    return self.render_json(entities)

  def _pre_post_hook(self):
    '''To run before POST.'''

  def _post_post_hook(self, entity):
    '''To run after POST.
    entity: recenty entity created.'''

  def create_model(self, **model_args):
    '''Create a new instance of model class.
    Specially for build key parents or special key ids.'''
    return self.model.from_dict(model_args)

  def post(self, **kwargs):
    '''POST verb.
    Returns a new entity created from request body as JSON formatted
    input'''
    self._pre_post_hook()
    new_entity_json = self.extract_json()
    new_entity_json.pop('$$key$$', None)
    new_entity_json.pop('$$id$$', None)
    entity = self.create_model(**new_entity_json)
    entity.put()
    self._post_post_hook(entity)

    return self.render_json(entity.to_dict())

  def _pre_put_hook(self):
    '''To run before PUT.'''

  def _post_put_hook(self, entity):
    '''To run after PUT.
    entity: recently modified entity.'''

  def update_model(self, _entity, **model_args):
    '''Update model'''
    _entity._populate_from_dict(model_args)

  def put(self, **kwargs):
    '''PUT verb.
    Modifies an entity with JSON info provided.'''
    self._pre_put_hook()
    key = kwargs.pop('key', None) 
    id = self.request.get('id', None) 

    if not key and not id:
      raise NoKeyOrIdError

    if key:
      try:
        entities = get_entity_by_key(key)
      except NoEntityError:
        return self.abort(404, '%s not found.' % self.model.__class__.__name__)
    elif id:
      entities = self.model.get_by_id(id)
      if not entities:
        return self.abort(404, '%s not found.' % self.model.__class__.__name__)

    entity_json = self.extract_json()
    self.update_model(entity, **entity_json)
    entity.put()
    self._post_put_hook(entity)

    return self.render_json(entity.to_dict())

  def _pre_delete_hook(self):
    '''To run before DELETE.'''

  def _post_delete_hook(self, entity):
    '''To run after DELETE.
    entity: recently deleted entity.'''

  def model_delete(self, entity):
    '''Deletion function.
    Useful if you don't want to delete the entity, just mark it as
    disabled.
    entity: entity to be deleted.'''
    entity.key.delete_async()

  def delete(self, **kwargs):
    '''DELETE verb.
    Deletes an entity.'''
    self._pre_delete_hook()
    key = kwargs.pop('key', None) 
    id = self.request.get('id', None) 

    if not key and not id:
      raise NoKeyOrIdError

    if key:
      entity = Key(urlsafe=key).get()
    elif id:
      self.model.get_by_id(id)

    if entity is None:
      return self.abort(404, '%s not found.' % self.model.__class__.__name__)

    self.model_delete(entity)
    self._post_delete_hook(entity)

    self.response.status = 200
    self.response.write(u'Model deletion successful')
