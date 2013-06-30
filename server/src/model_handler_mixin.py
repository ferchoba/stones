#!/usr/bin/env python
#-*- coding: utf-8 -*-

import logging

import webapp2_extras
from .model import Key

from google.appengine.ext import ndb

from .utils import *

from google.appengine.ext.ndb import Property


logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class to errors'''


class NoKeyOrIdError(Error):
    '''Occurs when no key or id is provided to find a single entity.'''


class NoEntityError(Error):
    '''Occurs when is imposible to find an entity.'''


class ModelHandlerMixin(object):
    """
        Mixin to add model CRUD to handler.

        In request, the 'k' argument is treated as key for instance model. You
        must to reserve this request argument.
    """
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
        @result: Array with found entities to be returned.'''
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
        rv = []
        for order in self.ordering:
            if not isinstance(order, Property):
                continue

            rv.append(order)
        return rv

    def get(self, **kwargs):
        '''GET verb.
        Returns a list of entities, even if the result is a single entity.'''

        @ndb.tasklet
        def get_entities(qry):
            _entities = yield qry.fetch_async()
            raise ndb.Return(_entities)

        self._pre_get_hook()
        key = kwargs.pop('key', None) or self.request.get('key')
        id = kwargs.get('id', None) or self.request.get('id')
        if key:
            entities = Key(urlsafe=key).get()
        elif id:
            entities = self.model.get_by_id(id)
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
        @entity: recenty entity created.'''

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
        @entity: recently modified entity.'''

    def update_model(self, _entity, **model_args):
        '''Update model'''
        _entity._populate_from_dict(model_args)

    def put(self, **kwargs):
        '''PUT verb.
        Modifies an entity with JSON info provided.'''
        self._pre_put_hook()
        key = kwargs.pop('key', None) or self.request.get('key') or \
            self.request.get('id')
        if not key:
            raise NoKeyOrIdError

        entity = Key(urlsafe=key).get() or self.model.get_by_id(key)
        if entity is None:
            raise NoEntityError

        entity_json = self.extract_json()
        self.update_model(entity, **entity_json)
        entity.put()
        self._post_put_hook(entity)

        return self.render_json(entity.to_dict())

    def _pre_delete_hook(self):
        '''To run before DELETE.'''

    def _post_delete_hook(self, entity):
        '''To run after DELETE.
        @entity: recently deleted entity.'''

    def model_delete(self, entity):
        '''Deletion function.
        Useful if you don't want to delete the entity, just mark it as
        disabled.
        @entity: entity to be deleted.'''
        entity.key.delete_async()

    def delete(self, **kwargs):
        '''DELETE verb.
        Deletes an entity.'''
        self._pre_delete_hook()
        key = kwargs.pop('key', None) or self.request.get('key') or \
            self.request.get('id')
        if not key:
            raise NoKeyOrIdError

        entity = Key(urlsafe=key).get() or self.model.get_by_id(key)
        if entity is None:
            raise NoEntityError

        self.model_delete(entity)
        self._post_delete_hook(entity)

        self.response.status = 200
        self.response.write(u'Model deletion successful')
