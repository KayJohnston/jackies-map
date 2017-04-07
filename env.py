import logging
import defs
logging.basicConfig(level = logging.INFO, format="[%(asctime)-8s.%(msecs)03d] [%(name)-10s] [%(levelname)7s] %(message)s", datefmt=defs.log_dateformat)

import argparse
import collections
import logging
import os
import platform
import sys
import threading
import time
import util
import pgnames
import system_internal as system
import station
import db_sqlite3
import env_backend as eb
import filter

log = logging.getLogger("env")

def log_versions(extra = []):
  sep = ' / '
  log.debug("Python: {} {}{}OS: {} {}{}".format(platform.python_version(), platform.architecture()[0], sep, platform.platform(), platform.machine(), sep + sep.join(extra) if extra else ''))


default_backend_name = 'db_sqlite3'
default_path = defs.default_path

_registered_backends = {}

def register_backend(name, fn):
  _registered_backends[name] = fn

def unregister_backend(name):
  del _registered_backends[name]

def _get_default_backend(path):
  db_path = os.path.join(os.path.normpath(path), os.path.normpath(global_args.db_file))
  db_sqlite3.log_versions()
  if not os.path.isfile(db_path):
    log.error("Error: EDDB/Coriolis data not found. Please run update.py to download this data and create the local database.")
    return None
  return db_sqlite3.open_db(db_path)

register_backend(default_backend_name, _get_default_backend)




def _make_known_system(s, keep_data=False):
  sysobj = system.KnownSystem(s)
  if keep_data:
    sysobj.data = s.copy()
  return sysobj

def _make_station(sy, st, keep_data = False):
  sysobj = _make_known_system(sy, keep_data) if not isinstance(sy, system.KnownSystem) else sy
  stnobj = station.Station(st, sysobj)
  if keep_data:
    stnobj.data = st
  return stnobj


class Env(object):
  def __init__(self, backend):
    log_versions(extra = ['Env Backend: {}'.format(backend.backend_name)])
    self.is_data_loaded = False
    self._backend = backend
    self._load_data()

  def close(self):
    if self._backend is not None:
      self._backend.close()

  @property
  def backend_name(self):
    return (self._backend.backend_name if self._backend else None)

  @property
  def filter_converters(self):
    return {'system': self.get_system, 'station': self.get_station}

  def parse_filter_string(self, s):
    return filter.parse_filter_string(s, self.filter_converters)

  def _get_as_filters(self, s):
    if s is None:
      return None
    elif util.is_str(s):
      return self.parse_filter_string(s)
    else:
      return s

  def parse_station(self, statstr):
    parts = statstr.split("/", 1)
    sysname = parts[0]
    statname = parts[1] if len(parts) > 1 else None
    return self.get_station(sysname, statname)

  def parse_stations(self, statlist):
    namelist = []
    for statstr in statlist:
      parts = statstr.split("/", 1)
      sysname = parts[0]
      statname = parts[1] if len(parts) > 1 else None
      namelist.append((sysname, statname))
    # Get the objects
    tmpdata_stn = self.get_stations([n for n in namelist if n[1] is not None])
    tmpdata_sys = self.parse_systems([n[0] for n in namelist if n[1] is None])
    # Now reorder the data to match the input list, and check if we lost any
    outdata = collections.OrderedDict()
    for i, (sy, st) in enumerate(namelist):
      if st is not None:
        sresult = tmpdata_stn.get((sy, st), None)
        outdata[statlist[i]] = sresult
      else:
        if sy in tmpdata_sys and tmpdata_sys[sy] is not None:
          outdata[statlist[i]] = station.Station.none(tmpdata_sys[sy])
        else:
          outdata[statlist[i]] = None
    return outdata

  def parse_system(self, sysstr):
    return self.get_system(sysstr)

  def parse_systems(self, sysstr):
    return self.get_systems(sysstr)

  def get_station_by_names(self, sysname, statname = None, keep_data = False):
    if statname is not None:
      (sysdata, stndata) = self._backend.get_station_by_names(sysname, statname)
      if sysdata is not None and stndata is not None:
        return _make_station(sysdata, stndata, keep_data)
    else:
      sys = self.get_system(sysname, keep_data)
      if sys is not None:
        return station.Station.none(sys)
    return None
  get_station = get_station_by_names

  def get_system_by_name(self, sysname, keep_data = False):
    # Check the input against the "fake" system format of "[123.4,56.7,-89.0]"...
    coords_data = util.parse_coords(sysname)
    if coords_data is not None:
      cx, cy, cz, name = coords_data
      return system.System(cx, cy, cz, name)
    else:
      result = self._backend.get_system_by_name(sysname)
      if result is not None:
        return _make_known_system(result, keep_data)
      else:
        return None
  get_system = get_system_by_name

  def get_system_by_id64(self, id64, keep_data = False):
    if util.is_str(id64):
      id64 = int(id64, 16)
    coords, cube_width, n2, _ = system.calculate_from_id64(id64)
    # Get a system prototype to steal its name
    sys_proto = pgnames.get_system(coords, cube_width)
    pname = sys_proto.name + str(n2)
    result = self._backend.get_system_by_id64(id64, fallback_name=pname)
    if result is not None:
      return _make_known_system(result, keep_data)
    else:
      return None

  def get_systems_by_name(self, sysnames, keep_data = False):
    co_list = {}
    db_list = []
    output = collections.OrderedDict()
    # Weed out fake systems first
    for s in sysnames:
      coords_data = util.parse_coords(s)
      if coords_data is not None:
        cx, cy, cz, name = coords_data
        co_list[s] = system.System(cx, cy, cz, name)
      else:
        db_list.append(s)
    # Now query for the real ones
    db_result = {}
    if any(db_list):
      result = self._backend.get_systems_by_name(db_list)
      db_result = {r.name.lower(): r for r in [_make_known_system(t, keep_data) for t in result]}
    for s in sysnames:
      if s.lower() in db_result:
        output[s] = db_result[s.lower()]
      elif s in co_list:
        output[s] = co_list[s]
      else:
        output[s] = None
    return output
  get_systems = get_systems_by_name

  def get_stations_by_names(self, names, keep_data = False):
    output = collections.OrderedDict()
    # Now query for the real ones
    if any(names):
      result = self._backend.get_stations_by_names(names)
      result = {(r.system.name.lower(), r.name.lower()): r for r in [_make_station(t[0], t[1], keep_data) for t in result]}
      for sy, st in names:
        output[(sy, st)] = result.get((sy.lower(), st.lower()), None)
    return output
  get_stations = get_stations_by_names

  def find_stations(self, args, filters = None, keep_station_data = False):
    sysobjs = args if isinstance(args, collections.Iterable) else [args]
    sysobjs = { s.id: s for s in sysobjs if s.id is not None }
    return [_make_station(sysobjs[stndata['eddb_system_id']], stndata, keep_data=keep_station_data) for stndata in self._backend.find_stations_by_system_id(list(sysobjs.keys()), filters=self._get_as_filters(filters))]

  def find_systems_by_aabb(self, vec_from, vec_to, buffer_from = 0.0, buffer_to = 0.0, filters = None):
    vec_from = util.get_as_position(vec_from)
    vec_to = util.get_as_position(vec_to)
    if vec_from is None or vec_to is None:
      raise ValueError("could not get a position from input AABB coords")
    min_x = min(vec_from.x, vec_to.x) - buffer_from
    min_y = min(vec_from.y, vec_to.y) - buffer_from
    min_z = min(vec_from.z, vec_to.z) - buffer_from
    max_x = max(vec_from.x, vec_to.x) + buffer_to
    max_y = max(vec_from.y, vec_to.y) + buffer_to
    max_z = max(vec_from.z, vec_to.z) + buffer_to
    return [system.KnownSystem(s) for s in self._backend.find_systems_by_aabb(min_x, min_y, min_z, max_x, max_y, max_z, filters=self._get_as_filters(filters))]
 
  def find_all_systems(self, filters = None, keep_data = False):
    for s in self._backend.find_all_systems(filters=self._get_as_filters(filters)):
      yield _make_known_system(s, keep_data=keep_data)

  def find_all_stations(self, filters = None, keep_data = False):
    for sy,st in self._backend.find_all_stations(filters=self._get_as_filters(filters)):
      yield _make_station(sy, st, keep_data=keep_data)

  def find_systems_by_name(self, name, filters = None, keep_data = False):
    for s in self._backend.find_systems_by_name_unsafe(name, mode=eb.FIND_EXACT, filters=self._get_as_filters(filters)):
      yield _make_known_system(s, keep_data)

  def find_systems_by_glob(self, name, filters = None, keep_data = False):
    for s in self._backend.find_systems_by_name_unsafe(name, mode=eb.FIND_GLOB, filters=self._get_as_filters(filters)):
      yield _make_known_system(s, keep_data)

  def find_systems_by_regex(self, name, filters = None, keep_data = False):
    for s in self._backend.find_systems_by_name_unsafe(name, mode=eb.FIND_REGEX, filters=self._get_as_filters(filters)):
      yield _make_known_system(s, keep_data)

  def find_stations_by_name(self, name, filters = None, keep_data = False):
    for (sy, st) in self._backend.find_stations_by_name_unsafe(name, mode=eb.FIND_EXACT, filters=self._get_as_filters(filters)):
      yield _make_station(sy, st, keep_data)

  def find_stations_by_glob(self, name, filters = None, keep_data = False):
    for (sy, st) in self._backend.find_stations_by_name_unsafe(name, mode=eb.FIND_GLOB, filters=self._get_as_filters(filters)):
      yield _make_station(sy, st, keep_data)

  def find_stations_by_regex(self, name, filters = None, keep_data = False):
    for (sy, st) in self._backend.find_stations_by_name_unsafe(name, mode=eb.FIND_REGEX, filters=self._get_as_filters(filters)):
      yield _make_station(sy, st, keep_data)

  def _load_data(self):
    try:
      self._load_coriolis_data()
      self.is_data_loaded = True
      log.debug("Data loaded")
    except Exception as ex:
      self.is_data_loaded = False
      log.error("Failed to load environment data: {}".format(ex))

  def _load_coriolis_data(self):
    self._coriolis_fsd_list = self._backend.retrieve_fsd_list()
    self.is_coriolis_data_loaded = True
    log.debug("Coriolis data loaded")

  @property
  def coriolis_fsd_list(self):
    return self._coriolis_fsd_list


class EnvWrapper(object):
  def __init__(self, path = default_path, backend = default_backend_name):
    self._backend = backend
    self._path = path

  def __enter__(self):
    self._close_env = False
    if not is_started(self._path, self._backend):
      start(self._path, self._backend)
      self._close_env = True
    if is_started(self._path, self._backend):
      return _open_backends[(self._backend, self._path)]
    else:
      raise RuntimeError("Failed to load environment")

  def __exit__(self, typ, value, traceback):
    if self._close_env:
      stop(self._path, self._backend)



_open_backends = {}

def start(path = default_path, backend = default_backend_name):
  if backend not in _registered_backends:
    raise ValueError("Specified backend name '{}' is not registered".format(backend))
  if not is_started(path, backend):
    backend_obj = _registered_backends[backend](path)
    if backend_obj is None or not isinstance(backend_obj, eb.EnvBackend):
      log.error("Failed to start environment: backend name '{}' failed to create object".format(backend))
      return False
    newdata = Env(backend_obj)
    if newdata.is_data_loaded:
      _open_backends[(backend, path)] = newdata
      return True
    else:
      return False
  else:
    return True


def is_started(path = default_path, backend = default_backend_name):
  return ((backend, path) in _open_backends and _open_backends[(backend, path)].is_data_loaded)


def stop(path = default_path, backend = default_backend_name):
  if (backend, path) in _open_backends:
    _open_backends[(backend, path)].close()
    del _open_backends[(backend, path)]
  return True


def use(path = default_path, backend = default_backend_name):
  return EnvWrapper(path, backend)


def set_verbosity(level):
  if level >= 3:
    logging.getLogger().setLevel(logging.DEBUG)
  elif level >= 2:
    logging.getLogger().setLevel(logging.INFO)
  elif level >= 1:
    logging.getLogger().setLevel(logging.WARN)
  elif level >= 0:
    logging.getLogger().setLevel(logging.ERROR)
  else:
    logging.getLogger().setLevel(logging.CRITICAL)

arg_parser = argparse.ArgumentParser(description = "Elite: Dangerous Tools", fromfile_prefix_chars="@", add_help=False)
arg_parser.add_argument("-v", "--verbose", type=int, default=2, help="Increases the logging output")
arg_parser.add_argument("--db-file", type=str, default=defs.default_db_file, help="Specifies the database file to use")
global_args, local_args = arg_parser.parse_known_args(sys.argv[1:])    

# Only try to parse args/set verbosity in non-interactive mode
if not util.is_interactive():
  set_verbosity(global_args.verbose)
