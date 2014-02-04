part of stones;

final Logger log = new Logger('stones.db');

/**
 * Error base class to stones.db
 */
class ModelException implements Exception {
}

/**
 * Represents a simplest form of datstore entity.
 * 
 * It has methods to communicate with server.
 * Implements the CRUD operations.
 */
@NgInjectableService()
class Entity {
  /**
   * URL to fetch data
   */
  String _url;
  get url => _url;
  
  /**
   * Angular Http service instance to make requests against a server
   */
  Http _http;
  
  /**
   * Headers to requests.
   */
  Map<String, String> _headers;
  
  /**
   * Entity properties.
   */
  Map<String, dynamic> _properties = {};
  
  /**
   * Modified entity properties
   */
  Map<String, dynamic> _mod_properties = {};
  
  /**
   * Gets entity property 
   */
  dynamic operator [](dynamic key) {
    if (this._mod_properties.containsKey(key)) {
      return this._mod_properties[key];
    }
    if (this._properties.containsKey(key)) {
      return this._properties[key];
    }
    return null;
  }
  
  /**
   * Sets entity property
   */
  void operator []=(String key, dynamic value) {
    this._mod_properties[key] = value;
  }
  
  Entity(this._http);
  
  /**
   * Build an entity from JSON.
   */
  Entity.fromJSON(json) {
    for (String key in json.keys) {
      this._properties[key] = json[key];
    }
  }
  
  /**
   * Returns a JSON representation of the entity
   */
  toJson () {
    return JSON.encode(this._properties);
  }
  
  /**
   * Gets one entity by key
   */
  Future get(String url, String key, {dynamic cache:false, Map<String, String> headers}) {
    this._url = url;
    var _url = [this._url, key].join('');
    this._headers = headers;
    Completer complete = new Completer();
    
    this._http.get(_url, headers:this._headers, cache:cache).then((response) {
      var data = response.data;
      var content_type = response.headers('content-type');
      
      if (content_type != 'application/json') {
        if (data is String) {
          try {
            data = JSON.decode(data);
          } catch (e) {
            complete.completeError('Impossible to decode server response:\n${data}');
            return;
          }
        } else if (data is! List) {
          data = JSON.encode(data);
        }
      }
      
      if (data is String) {
        data = JSON.decode(data);
      }
      
      complete.complete(new Entity.fromJSON(data));
    },
    onError: (response) {
      log.severe(response.toString());
      complete.completeError(response.data);
    });
    
    return complete.future;
  }
  
  /**
   * Returns if entity has been modified
   */
  bool get isModified => this._mod_properties.length > 0;
  
  /**
   * Returns entity key or id
   */
  dynamic get key {
    if (this._properties.containsKey('\$\$key\$\$')) {
      return this._properties['\$\$key\$\$'];
    }
    if (this._properties.containsKey('\$\$id\$\$')) {
      return this._properties['\$\$id\$\$'];
    }
    return null;
  }
  
  /**
   * Returns if entity is new or it has been saved before
   */
  bool get isNew => this.key == null;
  
  /**
   * Saves the entity to server
   * 
   * Sends only modifications over the entity 
   */
  Future save([String url]) {
    var self = this;
    if (url == null) {
      url = this._url;
    }
    Completer complete = new Completer();
    Future notModified = new Future.value(self);
    
    if (!this.isModified) {
      notModified.then((result) {
        complete.complete(result);
      });
      return complete.future;
    }
    
    var method = 'POST';
    if (!this.isNew) {
      method = 'PUT';
      url += this.key;
    }
    var data = this._mod_properties;
    
    this._http.call(url:url, method:method, data:data, headers:this._headers)
      .then((response) {
        var data = response.data;
        var content_type = response.headers('content-type');
        
        if (content_type != 'application/json') {
          if (data is String) {
            try {
              data = JSON.decode(data);
            } catch (e) {
              complete.completeError('Impossible to decode server response:\n${data}');
              return;
            }
          } else if (data is! List) {
            data = JSON.encode(data);
          }
        }
        
        if (data is String) {
          data = JSON.decode(data);
        }
        
        this._properties = {};
        for (key in data.keys) {
          this._properties[key] = data[key];
        }
         
        complete.complete(this);
      },
      onError: (response) {
        log.severe(response.toString());
        complete.completeError(response.data);        
      });
    
    return complete.future;
  }
}

/**
 * List of entities.
 * 
 * It Contains methods to deal with lists of entities.
 */
@NgInjectableService()
class Entities {
  /**
   * URL to get entities.
   */
  String _url;
  get url => _url;
  
  Http _http;

  /**
   * Constructor.
   */
  Entities(this._http);

  /**
   * Fetch a list of entities from server.
   */
  Future getEntities(String url, {dynamic cache:false, Map<String, String> params, Map<String, String> headers}) {
    this._url = url;
    var _headers = headers;
    Completer complete = new Completer();
    
    if (headers == null) {
      _headers = {'Accept':'application/json'};
    } else {
      _headers['Accept'] = 'application/json';
    }

    this._http.get(url, params:params, headers:_headers, cache:cache)
      .then((response) {
        var content_type = response.headers('content-type');
        var data = response.data;
        List<Entity> entities = new List<Entity>();

        if (content_type != 'application/json') {
          if (data is String) {
            try {
              data = JSON.decode(data);
            } catch (e) {
              complete.completeError('Impossible to decode server response:\n${data}');
              return;
            }
          } else if (data is! List) {
            data = JSON.encode(data);
          }
        }

        for (var ent in data) {
          if (ent is String) {
            ent = JSON.decode(ent);
          }
          entities.add(new Entity.fromJSON(ent));
        }
        complete.complete(entities);
      },
      onError:(response) {
        log.severe(response.toString());
        complete.completeError(response.data);
      });
    
    return complete.future;
  }
}