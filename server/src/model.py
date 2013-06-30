#!/usr/bin/env python
#-*- coding: utf-8 -*-

import datetime
import logging
import traceback

from google.appengine.ext import ndb
from google.appengine.ext.ndb.model import _StructuredGetForDictMixin as ndb_StructuredGetForDictMixin
from google.appengine.ext.ndb.google_imports import datastore_errors
from google.appengine.api.users import User

logger = logging.getLogger(__name__)

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'


def check_list(value):
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise datastore_errors.BadValueError('Expected list or tuple,'
                                             ' got %r' % (value,))


class _SetFromDictPropertyMixin(object):
    '''Mixin to add "from_dict" functionality.'''
    def _set_from_dict(self, value):
        '''Returns a proper value to property but not sets it.'''
        if self._repeated:
            check_list(value)
            return [self._do_validate(v) for v in value]
        return self._do_validate(value)


class _GetForCSVPropertyMixin(object):
    '''Mixin to add "for_csv" functionality.'''
    def _get_for_csv(self, instance):
        '''Returns a proper value to be inserted in a CSV cell.'''
        value = self._get_value(instance)
        if self._repeated:
            return ', '.join(value)
        return value


class StringProperty(ndb.StringProperty, _SetFromDictPropertyMixin,
                     _GetForCSVPropertyMixin):
    '''StringProperty modified.'''


class IntegerProperty(ndb.IntegerProperty, _SetFromDictPropertyMixin,
                      _GetForCSVPropertyMixin):
    ''''IntegerProperty modified.'''
    def _set_from_dict(self, value):
        '''Returns a proper value to property but not sets it.'''
        if self._repeated:
            check_list(value)
            value = [int(val) for val in value]
            return [self._do_validate(v) for v in value]
        return self._do_validate(int(value))



class FloatProperty(ndb.FloatProperty, _SetFromDictPropertyMixin,
                    _GetForCSVPropertyMixin):
    '''FloatProperty modified.'''
    def _set_from_dict(self, value):
        '''Returns a proper value to property but not sets it.'''
        if self._repeated:
            check_list(value)
            value = [float(val) for val in value]
            return [self._do_validate(v) for v in value]
        return self._do_validate(float(value))


class BooleanProperty(ndb.BooleanProperty, _SetFromDictPropertyMixin,
                      _GetForCSVPropertyMixin):
    '''BooleanProperty modified.'''
    def _set_from_dict(self, value):
        '''Returns a proper value to property but not sets it.'''
        def cast(val):
            if val in ['false', 'False']:
                return False
            return bool(val)

        if self._repeated:
            check_list(value)
            value = [cast(val) for val in value]
            return [self._do_validate(v) for v in value]
        return self._do_validate(cast(value))


class TextProperty(ndb.TextProperty, _SetFromDictPropertyMixin,
                   _GetForCSVPropertyMixin):
    '''TextProperty modified.'''


class BlobProperty(ndb.BlobProperty, _GetForCSVPropertyMixin):
    '''BlobProperty modified.'''
    def _set_from_dict(self, value):
        if isinstance(value, unicode):
            value = str(value)
        return self._do_validate(value)


class JsonProperty(ndb.JsonProperty, _SetFromDictPropertyMixin):
    '''JsonProperty modified.'''


class DateProperty(ndb.DateProperty, _GetForCSVPropertyMixin):
    '''DateProperty modified.'''
    def _set_from_dict(self, value):
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, DATE_FORMAT)
            value = value.date()
        return self._do_validate(value)


class DateTimeProperty(ndb.DateTimeProperty, _GetForCSVPropertyMixin):
    ''''DateTimeProperty modified.'''
    def _set_from_dict(self, value):
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, DATETIME_FORMAT)
        return self._do_validate(value)


class TimeProperty(ndb.TimeProperty, _GetForCSVPropertyMixin):
    '''TimeProperty modified.'''
    def _set_from_dict(self, value):
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, TIME_FORMAT)
            value = value.time()
        return self._do_validate(value)


class KeyProperty(ndb.KeyProperty):
    '''KeyProperty modified.'''
    def _set_from_dict(self, value):
        if isinstance(value, basestring):
            value = ndb.Key(urlsafe=value)
        elif isinstance(value, dict):
            if value.get('urlsafe_key', None):
                value = ndb.Key(urlsafe=value['urlsafe_key'])
            elif value.get('$$key$$', None):
                value = ndb.Key(urlsafe=value['$$key$$'])
        return self._do_validate(value)

    def _get_for_csv(self, instance):
        '''Returns a proper value to be inserted in a CSV cell.'''
        value = self._get_value(instance)
        if self._repeated:
            return ', '.join([val.urlsafe() for val in value])
        return value.urlsafe()



class UserProperty(ndb.UserProperty):
    def _set_from_dict(self, value):
        if isinstance(value, basestring):
            value = User(value)
        elif isinstance(value, dict):
            value = User(value['email'])
        return self._do_validate(value)

    def _get_for_csv(self, instance):
        value = self._get_value(instance)
        if value is None:
            return ''
        if self._repeated:
            return ', '.join([val.email() for val in value])
        return value.email()


class ComputedProperty(ndb.ComputedProperty, _GetForCSVPropertyMixin):
    def _set_from_dict(self, value):
        return None


class _StructuredSetFromDictMixin(object):
    '''Mixin to add "from_dict" functionality.'''
    def _set_from_dict(self, value):
        if self._repeated:
            check_list(value)
            _value = []
            for v in value:
                _value.append(self._modelclass.from_dict(v))
            return _value
        elif value is None:
            return None
        else:
            if not isinstance(value, dict):
                raise datastore_errors.BadValueError('Expected dict, got %r.'
                                                     % (value,))
            return self._modelclass.from_dict(value)


class StructuredProperty(ndb.StructuredProperty, _StructuredSetFromDictMixin):
    '''StructuredProperty modified.'''
    def _get_for_csv(self, instance):
        return None


class LocalStructuredProperty(ndb.LocalStructuredProperty,
                              _StructuredSetFromDictMixin):
    '''LocalStructuredProperty modified.'''
    def _get_for_csv(self, instance):
        return None


class Model(ndb.Model):
    '''New Model "from_dict" capable.'''
    def __unicode__(self):
        if hasattr(self, 'display'):
            if self.display is None:
                return u''
            return self.display
        else:
            return super(Model, self).__unicode__()

    @classmethod
    def _initial_values_from_dict(cls, value):
        '''Extract model attribute values from dict.'''
        if not isinstance(value, dict):
            raise datastore_errors.BadValueError('Expected dict, got %r.'
                                                 % (value,))

        props_names = value.keys()
        initial_values = {}
        for prop in cls._properties.itervalues():
            name = prop._code_name
            if name in props_names and not isinstance(prop, ndb.ComputedProperty):
                _value = value[name]
                if not _value is None:
                    has_set_from_dict = hasattr(prop, '_set_from_dict')
                    if not has_set_from_dict is None:
                        initial_values[name] = prop._set_from_dict(_value)
        return initial_values

    @classmethod
    def _from_dict(cls, value):
        '''Creates a new entity from data cointained in a dict, for example, a
        JSON structure.

        Args:
            value: dict with entity data.'''
        initial_values = cls._initial_values_from_dict(value)
        return cls(**initial_values)

    from_dict = _from_dict

    def _populate_from_dict(self, json):
        '''Populates the entity with data from dict.'''
        values = self._initial_values_from_dict(json)
        values_keys = values.keys()
        for unused, prop in self._properties.iteritems():
            if prop._code_name in values_keys:
                prop._set_value(self, values[prop._code_name])

    def _pre_put_hook(self):
        '''Determines if any inner ReferenceProperty must be saved after save
        the entity.'''
        self._unsaved_references = []
        for unused, prop in self._properties.iteritems():
            if isinstance(prop, ReferenceProperty):
                prop_value = prop._get_value(self)
                if prop._repeated:
                    for v_index, v in enumerate(prop_value):
                        if not v is None:
                            if not v.urlsafe_key and prop._original[v_index]:
                                self._unsaved_references.append(prop)
                                break
                else:
                    if not prop_value is None:
                        urlsafe_key = prop_value.urlsafe_key
                        if not urlsafe_key and prop._original:
                            # we need to save it after save the entity.
                            self._unsaved_references.append(prop)

    def _post_put_hook(self, future):
        if not self._unsaved_references:
            return

        self._save_again = False
        self_key = future.get_result()
        saved_originals = []
        for prop in self._unsaved_references:
            prop_value = prop._get_value(self)
            prop_original = prop._original
            if prop._repeated:
                inner_originals = []
                for v_index, v in enumerate(prop_value):
                    if not v.urlsafe_key:
                        if prop._allow_new:
                            original_args = prop_original[v_index]._to_dict()
                            if prop._is_child:
                                new_value = prop._original_class(
                                    parent=self_key, **original_args
                                )
                            else:
                                new_value = prop._original_class(
                                    **original_args
                                )
                            inner_originals.append(new_value.put_async())
                        else:
                            inner_originals.append(None)
                    else:
                        inner_originals.append(v.urlsafe_key)
                saved_originals.append(inner_originals)
            else:
                if not prop_value.urlsafe_key:
                    if prop._allow_new:
                        original_args = prop._original._to_dict()
                        if prop._is_child:
                            prop._original = prop._original_class(
                                parent=self_key,
                                **original_args
                            )
                        else:
                            prop._original = prop._original_class(
                                **original_args
                            )
                        saved_originals.append(prop._original.put_async())

        for index, reference_future in enumerate(saved_originals):
            prop = self._unsaved_references.pop(0)  # pop the 1st item always
            prop_value = prop._get_value(self)
            if prop._repeated:
                prop_value_shadow = []
                for v_index, v in enumerate(prop_value):
                    ref_future = reference_future[v_index]
                    if isinstance(ref_future, basestring):
                        ref_key = ref_future
                    elif not getattr(ref_future, 'get_result', None) is None:
                        ref_key = ref_future.get_result().urlsafe()
                    else:
                        ref_key = None

                    if not ref_key is None:
                        v.urlsafe_key = ref_key
                        prop_value_shadow.append(v)
                    self._save_again = True
                prop._set_value(self, prop_value_shadow)
            else:
                ref_key = reference_future.get_result()
                prop_value.urlsafe_key = ref_key.urlsafe()
                self._save_again = True

        if self._save_again:
            self.put_async()

    def to_dict(self):
        '''Returns a dict with special keys $$key$$ and $$id$$ added to
        entity values dict.'''
        _to_dict = super(Model, self).to_dict()
        if self._has_complete_key():
            _to_dict['$$id$$'] = self.key.id()
            _to_dict['$$key$$'] = self.key.urlsafe()
        return _to_dict


class _ReferenceModel(Model):
    urlsafe_key = StringProperty('k')
    display = StringProperty('d')


class ReferenceProperty(StructuredProperty):
    '''Property to store references to real entities with a description of the
    entity and string that represents urlsafe key.'''
    def __init__(self, modelclass=None, display=None, is_child=True,
                 allow_new=True, **kwds):
        '''Constructor.
        Args:
            modelclass: Entity model class.
            display: property or function which returns description for the
                entity. If display is a property, it should be StringProperty
                or TextProperty.
                If display is a function, it's going to
                receive the entity itself as unique argument.
                If no display is provided, we try to get a 'display' property
                inside modelclass.

        E. g.:
            class MyReferencedModel(Model):
                prop1 = ndb.StringProperty()

            class MyModel(Model):
                my_prop = ReferenceProperty(MyReferencedModel,
                                            display=MyReferencedModel.prop1)

        E. g.:
            class MyReferencedModel(Model):
                display = ndb.StringProperty()

            class MyModel(Model):
                my_prop = ReferenceProperty(MyReferencedModel)

        E. g.:
            class MyReferencedModel(Model):
                prop1 = ndb.StringProperty()

            class MyModel(Model):
                my_prop = ReferenceProperty(
                    MyReferencedModel,
                    display=lambda x: x.prop1 + ' says: Hello World!'
                )
        '''
        super(ReferenceProperty, self).__init__(_ReferenceModel, **kwds)
        self._display = display
        self._original_class = modelclass
        self._original = None
        if self._repeated:
            self._original = []
        self._is_child = is_child
        self._allow_new = allow_new

    def _fix_up(self, cls, code_name):
        super(ReferenceProperty, self)._fix_up(cls, code_name)
        if self._original_class is None:
            self._original_class = cls

        if self._display is None:
            try:
                self._display = getattr(self._original_class, 'display')
            except AttributeError:
                raise datastore_errors.BadValueError('No display property'
                                                     ' found.')
        else:
            if not isinstance(self._display, ndb.StringProperty) and \
                    not isinstance(self._display, ndb.TextProperty) and \
                    not callable(self._display):
                raise datastore_errors.BadValueError('Display argument is'
                                                     ' not valid.')

    def _set_value(self, entity, value):
        super(ReferenceProperty, self)._set_value(entity, value)
        self._original = value

    def _validate(self, value):
        if isinstance(value, dict):
            if 'urlsafe_key' in value:
                value = _ReferenceModel(**value)
            else:
                value = self._original_class.from_dict(value)
        if not isinstance(value, (self._original_class, _ReferenceModel)):
            raise datastore_errors.BadValueError(
                'Expected %s or ReferenceProperty, got %r.'
                % (self._original_class.__name__, (value,))
            )
        return value

    def _to_base_type(self, value):
        if isinstance(value, _ReferenceModel):
            return value

        urlsafe_key = ''
        display = ''
        if not value.key is None:
            urlsafe_key = value.key.urlsafe()
        if isinstance(self._display, ndb.StringProperty) or \
                isinstance(self._display, ndb.TextProperty):
            display = getattr(value, self._display._code_name)
        elif callable(self._display):
            display = self._display(value)

        return _ReferenceModel(urlsafe_key=urlsafe_key, display=display)

    def _from_base_type(self, value):
        return value

    def _set_from_dict(self, value):
        if self._repeated:
            if not isinstance(value, (list, tuple, set, frozenset)):
                raise datastore_errors.BadValueError('Expected list or tuple,'
                                                     ' got %r' % (value,))
            _value = []
            for v in value:
                urlsafe_key = v.get('urlsafe_key', '') or v.get('$$key$$', '')
                if not urlsafe_key:
                    ref = self._original_class.from_dict(v)
                else:
                    ref = _ReferenceModel(urlsafe_key=urlsafe_key,
                                          display=v.get('display', ''))
                    display = v.get('display', None)
                    if not display:
                        entity = ndb.Key(urlsafe=urlsafe_key).get()
                        ref = self._to_base_type(entity)
                _value.append(ref)
            return _value
        elif value is None:
            return None
        else:
            if not isinstance(value, dict):
                raise datastore_errors.BadValueError('Expected dict, got %r.'
                                                     % (value,))
            urlsafe_key = value.get('urlsafe_key', '') or value.get('$$key$$',
                                                                    '')
            if not urlsafe_key:
                ref = self._original_class.from_dict(value)
            else:
                ref = _ReferenceModel(urlsafe_key=urlsafe_key,
                                      display=value.get('display', ''))
                display = value.get('display', None)
                if not display:
                    entity = ndb.Key(urlsafe=urlsafe_key).get()
                    ref = self._to_base_type(entity)
            return ref

    def _get_for_csv(self, instance):
        value = self._get_value(instance)
        if value is None:
            return ''
        if self._repeated:
            return ', '.join([val.display for val in value])
        return value.display

    def _get_reference(self, entity):
        '''Retrieve original model.'''
        value = self._get_value(entity)
        if value.urlsafe_key:
            return ndb.Key(urlsafe=value.urlsafe_key).get()
        return None

    @classmethod
    def _get_reference_model_from_dict(cls, value):
        if not isinstance(value, dict):
            raise datastore_errors.BadValueError('Expected dict, got %r.'
                                                 % (value,))
        return _ReferenceModel(**value)


Key = ndb.Key

__all__ = ['Model', 'Key', 'datastore_errors', '_ReferenceModel']
for _name, _object in globals().items():
    if ((_name.endswith('Property') and issubclass(_object, ndb.Property)) or
        (_name.endswith('Error') and issubclass(_object, Exception))):
        __all__.append(_name)