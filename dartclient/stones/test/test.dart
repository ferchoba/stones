import 'package:logging/logging.dart' as logging;
import 'package:unittest/unittest.dart';
import 'package:unittest/html_enhanced_config.dart';
import 'package:di/di.dart';
import 'dart:convert';
import 'dart:async';
import 'package:angular/mock/module.dart';

import 'package:stones/stones.dart';

final logging.Logger log = new logging.Logger('test.stones');

main () {
  logging.Logger.root.level = logging.Level.ALL;
  logging.Logger.root.onRecord.listen((logging.LogRecord rec) {
    print('${rec.level.name}: ${rec.time}: ${rec.message}');
  });
  
  setUp(() {
    setUpInjector();
    module((Module m) => m.install(new Stones()));
  });
  tearDown(tearDownInjector);
  useHtmlEnhancedConfiguration();
  group('Datastore communcation', () {
    test('Entities fetch', async(inject((Injector injector, MockHttpBackend backend) {
      var url = '/entities/';
      var entitiesService = injector.get(Entities);
      var sample_entity = new Entity.fromJSON(JSON.decode('{"label":"Label", "display":"Display"}'));
      var sample_entities = [sample_entity];
      var response_headers = {'Content-Type': 'aplication/json'};
      
      backend.expectGET(url).respond(200, JSON.encode(sample_entities), response_headers);
      entitiesService.getEntities(url).then((entities) {
        expect(entities.length, equals(1));
        expect(entities[0]['label'], equals('Label'));
        expect(entities[0]['display'], equals('Display'));
      });
      
      backend.expectGET(url).respond(200, 'hhhhhsssss!!!hhsgghshs');
      entitiesService.getEntities(url).then((entities) {
        throw 'Stones is wrong... so wrong... no positive response shoul`d be here!';
      }, onError: (reason) {
        expect(reason, equals('Impossible to decode server response:\nhhhhhsssss!!!hhsgghshs'));
      });

      backend.expectGET(url).respond(500, 'Internal Server Error');
      entitiesService.getEntities(url).then((entities) {
        throw 'Stones is wrong... so wrong... no positive response shoul`d be here!';
      }, onError: (reason) {
        expect(reason, equals('Internal Server Error'));
      });

      microLeap();
      backend.flush();
      microLeap();
    })));

    test('Entity creation', async(inject((Injector injector, MockHttpBackend backend) {
      var url = '/entities/';
      var entityService = injector.get(Entity);
      var sample_entity = new Entity.fromJSON(JSON.decode('{"\$\$key\$\$":"abcde", "label":"Label", "display":"Display"}'));
      var response_headers = {'Content-Type': 'aplication/json'};
      
      backend.expectGET([url, sample_entity.key].join(''))
         .respond(200, JSON.encode(sample_entity), response_headers);
      entityService.get(url, sample_entity.key).then((entity) {
        expect(entity['label'], equals('Label'));
        expect(entity['display'], equals('Display'));
        expect(entity.isModified, equals(false));
      });
      
      backend.expectGET([url, sample_entity.key].join(''))
        .respond(200, 'hhhhhsssss!!!hhsgghshs');
      entityService.get(url, sample_entity.key).then((entity) {
        throw 'Stones is wrong... so wrong... no positive response shoul`d be here!';
      }, onError: (reason) {
        expect(reason, equals('Impossible to decode server response:\nhhhhhsssss!!!hhsgghshs'));
      });

      backend.expectGET([url, sample_entity.key].join(''))
        .respond(500, 'Internal Server Error');
      entityService.get(url, sample_entity.key).then((entity) {
        throw 'Stones is wrong... so wrong... no positive response shoul`d be here!';
      }, onError: (reason) {
        expect(reason, equals('Internal Server Error'));
      });

      microLeap();
      backend.flush();
      microLeap();
    })));

    test('Entity modification', async(inject((Injector injector, MockHttpBackend backend) {
      var url = '/entities/';
      var entityService = injector.get(Entity);
      var entity = new Entity.fromJSON(JSON.decode('{"\$\$key\$\$":"abcde", "label":"Label", "display":"Display"}'));
      var response_headers = {'Content-Type': 'aplication/json'};
      
      expect(entity.key, equals('abcde'));
      expect(entity.isNew, equals(false));
      expect(entity['label'], equals('Label'));
      expect(entity['display'], equals('Display'));
      expect(entity.isModified, equals(false));
      entity['label'] = 'Other label';
      expect(entity['label'], equals('Other label'));
      expect(entity.isModified, equals(true));
      
      backend.expectPUT([url, entity.key].join(''))
        .respond(200, '{"\$\$key\$\$":"abcde", "label":"Other label", "display":"Display"}');
      entity.save([url, entity.key].join('')).then((_entity) {
        expect(_entity, same(entity));
      });
      
      microLeap();
      backend.flush();
      microLeap();
    })));
  });
}