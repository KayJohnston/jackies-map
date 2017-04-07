import collections
import decimal
import defs
import env_backend as eb
import filter
import id64data
import json
import logging
import math
import os
import pgnames
import re
import sqlite3
import time
import util
import vector3

log = logging.getLogger("db_sqlite3")

schema_version = 7

_find_operators = ['=','LIKE','REGEXP']
# This is nasty, and it may well not be used up in the main code
_bad_char_regex = re.compile("[^a-zA-Z0-9'&+:*^%_?.,/#@!=`() -]")


def _regexp(expr, item):
  rgx = re.compile(expr)
  return rgx.search(item) is not None


def _vec3_len(x1, y1, z1, x2, y2, z2):
  xdiff = (x2-x1)
  ydiff = (y2-y1)
  zdiff = (z2-z1)
  return math.sqrt(xdiff*xdiff + ydiff*ydiff + zdiff*zdiff)


def _vec3_angle(x1, y1, z1, x2, y2, z2):
  return vector3.Vector3(x1, y1, z1).angle_to(vector3.Vector3(x2, y2, z2))


def log_versions():
  log.debug("SQLite3: {} / PySQLite: {}".format(sqlite3.sqlite_version, sqlite3.version))


def open_db(filename = defs.default_db_path, check_version = True):
  conn = sqlite3.connect(filename)
  conn.row_factory = sqlite3.Row
  conn.create_function("REGEXP", 2, _regexp)
  conn.create_function("vec3_len", 6, _vec3_len)
  conn.create_function("vec3_angle", 6, _vec3_angle)
 
  if check_version:
    c = conn.cursor()
    c.execute('SELECT db_version FROM edts_info')
    (db_version, ) = c.fetchone()
    if db_version != schema_version:
      log.warning("DB file's schema version {0} does not match the expected version {1}.".format(db_version, schema_version))
      log.warning("This is likely to cause errors; you may wish to rebuild the database by running update.py")
    log.debug("DB connection opened")
  return SQLite3DBConnection(conn)


def initialise_db(filename = defs.default_db_path):
  dbc = open_db(filename, check_version=False)
  dbc._create_tables()
  return dbc


class SQLite3DBConnection(eb.EnvBackend):
  def __init__(self, conn):
    super(SQLite3DBConnection, self).__init__("db_sqlite3")
    self._conn = conn

  def close(self):
    self._conn.close()
    log.debug("DB connection closed")

  def _create_tables(self):
    log.debug("Creating tables...")
    c = self._conn.cursor()
    c.execute('CREATE TABLE edts_info (db_version INTEGER, db_mtime INTEGER)')
    c.execute('INSERT INTO edts_info VALUES (?, ?)', (schema_version, int(time.time())))

    c.execute('CREATE TABLE systems (edsm_id INTEGER NOT NULL, name TEXT COLLATE NOCASE NOT NULL, pos_x REAL NOT NULL, pos_y REAL NOT NULL, pos_z REAL NOT NULL, eddb_id INTEGER, id64 INTEGER, needs_permit BOOLEAN, allegiance TEXT, data TEXT)')
    c.execute('CREATE TABLE stations (eddb_id INTEGER NOT NULL, eddb_system_id INTEGER NOT NULL, name TEXT COLLATE NOCASE NOT NULL, sc_distance INTEGER, station_type TEXT, max_pad_size TEXT, data TEXT)')
    c.execute('CREATE TABLE coriolis_fsds (id TEXT NOT NULL, data TEXT NOT NULL)')

    self._conn.commit()
    log.debug("Done.")

  def _generate_systems(self, systems):
    for s in systems:
      s_id64 = id64data.known_systems.get(s['name'].lower(), None)
      yield (int(s['id']), s['name'], float(s['coords']['x']), float(s['coords']['y']), float(s['coords']['z']), s_id64)

  def _generate_systems_update(self, systems):
    for s in systems:
      yield (int(s['id']), bool(s['needs_permit']), s['allegiance'], json.dumps(s), s['edsm_id'])

  def _generate_stations(self, stations):
    for s in stations:
      yield (int(s['id']), int(s['system_id']), s['name'], int(s['distance_to_star']) if s['distance_to_star'] is not None else None, s['type'], s['max_landing_pad_size'], json.dumps(s))

  def _generate_coriolis_fsds(self, fsds):
    for fsd in fsds:
      yield ('{0}{1}'.format(fsd['class'], fsd['rating']), json.dumps(fsd))

  def populate_table_systems(self, many):
    c = self._conn.cursor()
    log.debug("Going for INSERT INTO systems...")
    c.executemany('INSERT INTO systems VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)', self._generate_systems(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.".format(c.rowcount))
    log.debug("Going to add indexes to systems for name, pos_x/pos_y/pos_z, edsm_id...")
    c.execute('CREATE INDEX idx_systems_name ON systems (name COLLATE NOCASE)')
    c.execute('CREATE INDEX idx_systems_pos ON systems (pos_x, pos_y, pos_z)')
    c.execute('CREATE INDEX idx_systems_edsm_id ON systems (edsm_id)')
    c.execute('CREATE INDEX idx_systems_id64 ON systems (id64)')
    self._conn.commit()
    log.debug("Indexes added.")


  def update_table_systems(self, many):
    c = self._conn.cursor()
    log.debug("Going for UPDATE systems...")
    c.executemany('UPDATE systems SET eddb_id=?, needs_permit=?, allegiance=?, data=? WHERE edsm_id=?', self._generate_systems_update(many))
    self._conn.commit()
    log.debug("Done, {} rows affected.".format(c.rowcount))
    log.debug("Going to add indexes to systems for eddb_id...")
    c.execute('CREATE INDEX idx_systems_eddb_id ON systems (eddb_id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def populate_table_stations(self, many):
    c = self._conn.cursor()
    log.debug("Going for INSERT INTO stations...")
    c.executemany('INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?, ?)', self._generate_stations(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.".format(c.rowcount))
    log.debug("Going to add indexes to stations for name, eddb_system_id...")
    c.execute('CREATE INDEX idx_stations_name ON stations (name COLLATE NOCASE)')
    c.execute('CREATE INDEX idx_stations_sysid ON stations (eddb_system_id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def populate_table_coriolis_fsds(self, many):
    log.debug("Going for INSERT INTO coriolis_fsds...")
    c = self._conn.cursor()
    c.executemany('INSERT INTO coriolis_fsds VALUES (?, ?)', self._generate_coriolis_fsds(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.".format(c.rowcount))
    log.debug("Going to add indexes to coriolis_fsds for id...")
    c.execute('CREATE INDEX idx_coriolis_fsds_id ON coriolis_fsds (id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def retrieve_fsd_list(self):
    c = self._conn.cursor()
    cmd = 'SELECT id, data FROM coriolis_fsds'
    log.debug("Executing: {}".format(cmd))
    c.execute(cmd)
    results = c.fetchall()
    log.debug("Done.")
    return dict([(k, json.loads(v)) for (k, v) in results])

  def get_system_by_id64(self, id64, fallback_name = None):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE id64 = ?'
    data = (id64, )
    if fallback_name:
      cmd += ' OR name = ?'
      data = (id64, fallback_name)
    log.debug("Executing: {}; id64 = {}, name = {}".format(cmd, id64, fallback_name))
    c.execute(cmd, data)
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return _process_system_result(result)
    else:
      return None

  def get_system_by_name(self, name):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE name = ?'
    log.debug("Executing: {}; name = {}".format(cmd, name))
    c.execute(cmd, (name, ))
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return _process_system_result(result)
    else:
      return None

  def get_systems_by_name(self, names):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE name IN ({})'.format(','.join(['?'] * len(names)))
    log.debug("Executing: {}; names = {}".format(cmd, names))
    c.execute(cmd, names)
    result = c.fetchall()
    log.debug("Done.")
    if result is not None:
      return [_process_system_result(r) for r in result]
    else:
      return None

  def get_station_by_names(self, sysname, stnname):
    c = self._conn.cursor()
    cmd = 'SELECT sy.name AS name, sy.pos_x AS pos_x, sy.pos_y AS pos_y, sy.pos_z AS pos_z, sy.id64 AS id64, sy.data AS data, st.data AS stndata FROM systems sy, stations st WHERE sy.name = ? AND st.name = ? AND sy.eddb_id = st.eddb_system_id'
    log.debug("Executing: {}; sysname = {}, stnname = {}".format(cmd, sysname, stnname))
    c.execute(cmd, (sysname, stnname))
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return (_process_system_result(result), json.loads(result['stndata']))
    else:
      return (None, None)

  def get_stations_by_names(self, names):
    c = self._conn.cursor()
    extra_cmd = ' OR '.join(['sy.name = ? AND st.name = ?'] * len(names))
    cmd = 'SELECT sy.name AS name, sy.pos_x AS pos_x, sy.pos_y AS pos_y, sy.pos_z AS pos_z, sy.id64 AS id64, sy.data AS data, st.data AS stndata FROM systems sy, stations st WHERE sy.eddb_id = st.eddb_system_id AND ({})'.format(extra_cmd)
    log.debug("Executing: {}; names = {}".format(cmd, names))
    c.execute(cmd, [n for sublist in names for n in sublist])
    result = c.fetchall()
    log.debug("Done.")
    if result is not None:
      return [(_process_system_result(r), json.loads(r['stndata'])) for r in result]
    else:
      return (None, None)

  def find_stations_by_system_id(self, args, filters = None):
    sysids = args if isinstance(args, collections.Iterable) else [args]
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['stations'],
      ['stations.eddb_system_id', 'stations.data'],
      ['eddb_system_id IN ({})'.format(','.join(['?'] * len(sysids)))],
      [],
      sysids,
      filters)
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    results = c.fetchall()
    log.debug("Done, {} results.".format(len(results)))
    return [{ k: v for d in [{ 'eddb_system_id': r[0] }, json.loads(r[1])] for k, v in d.items()} for r in results]

  def find_systems_by_aabb(self, min_x, min_y, min_z, max_x, max_y, max_z, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      ['? <= systems.pos_x', 'systems.pos_x < ?', '? <= systems.pos_y', 'systems.pos_y < ?', '? <= systems.pos_z', 'systems.pos_z < ?'],
      [],
      [min_x, max_x, min_y, max_y, min_z, max_z],
      filters)
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    results = c.fetchall()
    log.debug("Done, {} results.".format(len(results)))
    return [_process_system_result(r) for r in results]
    
  def find_systems_by_name(self, name, mode = eb.FIND_EXACT, filters = None):
    # return self.find_systems_by_name_safe(name, mode, filters)
    return self.find_systems_by_name_unsafe(name, mode, filters)

  def find_stations_by_name(self, name, mode = eb.FIND_EXACT, filters = None):
    # return self.find_stations_by_name_safe(name, mode, filters)
    return self.find_stations_by_name_unsafe(name, mode, filters)

  def find_systems_by_name_safe(self, name, mode = eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      ['systems.name {} ?'.format(_find_operators[mode])],
      [],
      [name],
      filters)
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  def find_stations_by_name_safe(self, name, mode = eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      ['stations.name {} ?'.format(_find_operators[mode])],
      [],
      [name],
      filters)
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  # WARNING: VERY UNSAFE, USE WITH CARE
  # These methods exist due to a bug in the Python sqlite3 module
  # Using bound parameters as the safe versions do results in indexes being ignored
  # This significantly slows down searches (~500x at time of writing) due to doing full table scans
  # So, these methods are fast but vulnerable to SQL injection due to use of string literals
  # This will hopefully be unnecessary in Python 2.7.11+ / 3.6.0+ if porting of a newer pysqlite2 version is completed
  def find_systems_by_name_unsafe(self, name, mode=eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    name = _bad_char_regex.sub("", name)
    name = name.replace("'", r"''")
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      ["systems.name {} '{}'".format(_find_operators[mode], name)],
      [],
      [],
      filters)
    log.debug("Executing (U): {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  def find_stations_by_name_unsafe(self, name, mode=eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    name = _bad_char_regex.sub("", name)
    name = name.replace("'", r"''")
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      ["stations.name {} '{}'".format(_find_operators[mode], name)],
      [],
      [],
      filters)
    c = self._conn.cursor()
    log.debug("Executing (U): {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  # Slow as sin; avoid if at all possible
  def find_all_systems(self, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      [],
      [],
      [],
      filters)
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  # Slow as sin; avoid if at all possible
  def find_all_stations(self, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      [],
      [],
      [],
      filters) 
    log.debug("Executing: {}; params = {}".format(cmd, params))
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  def get_populated_systems(self):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, data FROM systems WHERE allegiance IS NOT NULL'
    log.debug("Executing: {}".format(cmd))
    c.execute(cmd)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()


def _process_system_result(result):
  if 'data' in result.keys() and result['data'] is not None:
    data = json.loads(result['data'])
    data['id64'] = result['id64']
    return data
  else:
    return {'name': result['name'], 'x': result['pos_x'], 'y': result['pos_y'], 'z': result['pos_z'], 'id64': result['id64']}

def _construct_query(qtables, select, qfilter, select_params = [], filter_params = [], filters = None):
  tables = qtables
  qmodifier = []
  qmodifier_params = []
  # Apply any user-defined filters
  if filters:
    fsql = filter.generate_filter_sql(filters)
    tables = set(qtables + fsql['tables'])
    select = select + fsql['select'][0]
    qfilter = qfilter + fsql['filter'][0]
    select_params += fsql['select'][1]
    filter_params += fsql['filter'][1]
    group = fsql['group'][0]
    group_params = fsql['group'][1]
    # Hack, since we can't really know this before here :(
    if 'stations' in tables and 'systems' in tables:
      qfilter.append("systems.eddb_id=stations.eddb_system_id")
      # More hack: if we weren't originally joining on stations, group results by system
      if 'stations' not in qtables:
        group.append('systems.eddb_id')
    # If we have any groups/ordering/limiting, set it up
    if any(group):
      qmodifier.append('GROUP BY {}'.format(', '.join(group)))
      qmodifier_params += group_params
    if any(fsql['order'][0]):
      qmodifier.append('ORDER BY {}'.format(', '.join(fsql['order'][0])))
      qmodifier_params += fsql['order'][1]
    if fsql['limit']:
      qmodifier.append('LIMIT {}'.format(fsql['limit']))
  else:
    # Still need to check this
    if 'stations' in tables and 'systems' in tables:
      qfilter.append("systems.eddb_id=stations.eddb_system_id")

  q1 = 'SELECT {} FROM {}'.format(','.join(select), ','.join(tables))
  q2 = 'WHERE {}'.format(' AND '.join(qfilter)) if any(qfilter) else ''
  q3 = ' '.join(qmodifier)
  query = '{} {} {}'.format(q1, q2, q3)
  params = select_params + filter_params + qmodifier_params
  return (query, params)
