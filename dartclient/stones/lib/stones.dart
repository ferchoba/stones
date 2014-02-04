/**
 * Client side library to work with stones.
 */
library stones;

import 'package:logging/logging.dart';
import 'package:angular/angular.dart';
import 'package:di/di.dart';
import 'dart:async';
import 'dart:convert';

@MirrorsUsed(override: '*')
import 'dart:mirrors';

part 'db.dart';

class Stones extends Module {
  Stones () {
    type(Entities);
    type(Entity);
  }
}