
class Station(object):
  def __init__(self, obj, sysobj):
    self.distance = int(obj['distance_to_star']) if (obj is not None and 'distance_to_star' in obj and obj['distance_to_star'] is not None) else None
    self.uses_sc = (self.distance is not None)
    self.system = sysobj
    self.name = obj['name'] if obj is not None else None
    self.station_type = obj['type'] if obj is not None else None
    self.has_fuel = bool(obj['has_refuel']) if obj is not None else False
    self.max_pad_size = obj['max_landing_pad_size'] if obj is not None else 'L'
    self.is_planetary = obj['is_planetary'] if obj is not None else False

  def __str__(self):
    if self.name is not None:
      return u"{0}/{1}".format(self.system_name, self.name)
    else:
      return u"{0}/(none)".format(self.system_name)

  def __repr__(self):
    return u"Station({0})".format(self.__str__())

  def distance_to(self, other):
    return (self.position - other.position).length

  def has_pad(self, pad_size):
    if self.name is None:
      return False
    if pad_size.upper() == 'L' and self.max_pad_size != 'L':
      return False
    return True

  @classmethod
  def none(self, sysobj):
    return self(None, sysobj)

  @property
  def position(self):
    return self.system.position

  @property
  def needs_permit(self):
    return self.system.needs_permit

  @property
  def system_name(self):
    return self.system.name

  def to_string(self, inc_sys = True):
    if self.name is None:
      return self.system_name

    return u"{0}{1} ({2}Ls, {3})".format(
        (self.system_name + ", ") if inc_sys else "",
        self.name, self.distance if self.distance is not None else "???",
        self.station_type if self.station_type is not None else "???")

  def __eq__(self, other):
    if isinstance(other, Station):
      return (self.system == other.system and self.name == other.name)
    else:
      return NotImplemented

  def __hash__(self):
    return u"{0}/{1}".format(self.system_name, self.name).__hash__()
