#!/usr/bin/env python
#-*- coding:utf-8 -*-

import datetime
import logging
try:
    import simplejson as json
except ImportError:
    import json

import csv
import codecs
import cStringIO

import webapp2
from google.appengine.ext import ndb
from google.appengine.api import users as google_users
from babel.support import LazyProxy
import model

import unittest
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util


logger = logging.getLogger(__name__)
__all__ = ['dbg', 'JSONEncoder', 'clear_id', 'BaseTestCase']


def clear_id(id):
    """
        Clear id to add it to model creation.
        Converts to ascii, replace spaces, and more.
    """
    map_ = {u'ñ': 'n', u'á': 'a', u'é': 'e', u'í': u'i', u'ó': 'o', u'ú': 'u'}
    _id = id
    _id = _id.strip().lower()
    _id = _id.replace(' ', '-')
    for old, new in map_.iteritems():
        _id = _id.replace(old, new)
    return _id


def dbg():
    """
        Enter pdb in App Engine
        Renable system streams for it.
    """
    import pdb
    import sys
    pdb.Pdb(
        stdin=getattr(sys, '__stdin__'),
        stdout=getattr(sys, '__stderr__')).set_trace(sys._getframe().f_back)


class JSONEncoder(json.JSONEncoder):
    """
        Encoder for models dumps.
    """
    def __init__(self, *args, **kwargs):
        kwargs['ensure_ascii'] = True
        super(JSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
            return obj.strftime(model.DATETIME_FORMAT)
        elif isinstance(obj, datetime.date):
            return obj.strftime(model.DATE_FORMAT)
        elif isinstance(obj, datetime.time):
            return obj.strftime(model.TIME_FORMAT)
        elif isinstance(obj, ndb.Query):
            return list(obj)
        elif isinstance(obj, LazyProxy):
            return unicode(obj)
        elif isinstance(obj, ndb.Model):
            return obj.to_dict()
        elif isinstance(obj, model.Key):
            return obj.get().to_dict()
        elif isinstance(obj, google_users.User):
            return {
                'email': obj.email(),
                'user_id': obj.user_id(),
                'nickname': obj.nickname(),
            }
        else:
            return json.JSONEncoder.default(self, obj)


class BaseTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        self.app = webapp2.import_string('main.app')

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        # Consistency policy to HRD.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()

    def tearDown(self):
        self.testbed.deactivate()
