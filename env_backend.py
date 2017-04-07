
FIND_EXACT = 0
FIND_GLOB = 1
FIND_REGEX = 2

class EnvBackend(object):
  def __init__(self, backend_name):
    self.backend_name = backend_name

  def retrieve_fsd_list(self):
    raise NotImplementedError("Invalid use of base EnvBackend retrieve_fsd_list method")

  def get_system_by_id64(self, id64, fallback_name = None):
    raise NotImplementedError("Invalid use of base EnvBackend get_system_by_id64 method")

  def get_system_by_name(self, name):
    raise NotImplementedError("Invalid use of base EnvBackend get_system_by_name method")

  def get_systems_by_name(self, names):
    raise NotImplementedError("Invalid use of base EnvBackend get_systems_by_name method")

  def get_station_by_names(self, sysname, stnname):
    raise NotImplementedError("Invalid use of base EnvBackend get_station_by_names method")

  def get_stations_by_names(self, names):
    raise NotImplementedError("Invalid use of base EnvBackend get_stations_by_names method")

  def find_stations_by_system_id(self, args, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend get_stations_by_system_id method")

  def find_systems_by_aabb(self, min_x, min_y, min_z, max_x, max_y, max_z, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend get_systems_by_aabb method")

  def find_systems_by_name(self, name, mode = FIND_EXACT, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend find_systems_by_name method")

  def find_stations_by_name(self, name, mode = FIND_EXACT, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend find_stations_by_name method")

  def find_all_systems(self, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend get_all_systems method")

  def find_all_stations(self, filter = None):
    raise NotImplementedError("Invalid use of base EnvBackend get_all_stations method")
