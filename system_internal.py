import pgnames
import sector
import util
import vector3


class System(object):
  def __init__(self, x, y, z, name = None, id64 = None):
    self._position = vector3.Vector3(float(x), float(y), float(z))
    self._name = name
    self._id = None
    self._id64 = id64
    self.uses_sc = False
    self._hash = u"{}/{},{},{}".format(self.name, self.position.x, self.position.y, self.position.z).__hash__()

  @property
  def system_name(self):
    return self.name

  @property
  def position(self):
    return self._position

  @property
  def name(self):
    return self._name

  @property
  def id(self):
    return self._id

  @property
  def id64(self):
    if self._id64 is None:
      if self.name is not None:
        m = pgnames.get_system_fragments(self.name)
        if m is not None:
          self._id64 = calculate_id64(self.position, m['MCode'], m['N2'])
    return self._id64

  @property
  def sector(self):
    return pgnames.get_sector(self.position)

  def to_string(self, use_long = False):
    if use_long:
      return u"{0} ({1:.2f}, {2:.2f}, {3:.2f})".format(self.name, self.position.x, self.position.y, self.position.z)
    else:
      return u"{0}".format(self.name)

  def __str__(self):
    return self.to_string()

  def __repr__(self):
    return u"System({})".format(self.name)

  def distance_to(self, other):
    other = util.get_as_position(other)
    if other is not None:
      return (self.position - other).length
    else:
      raise ValueError("distance_to argument must be position-like object")

  def __eq__(self, other):
    if isinstance(other, System):
      return (self.name == other.name and self.position == other.position)
    else:
      return NotImplemented

  def __hash__(self):
    return self._hash


class PGSystemPrototype(System):
  def __init__(self, x, y, z, name, sector, uncertainty):
    super(PGSystemPrototype, self).__init__(x, y, z, name)
    self.uncertainty = uncertainty
    self._sector = sector

  @property
  def sector(self):
    return self._sector

  def __repr__(self):
    return u"PGSystemPrototype({})".format(self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y, self.position.z))


class PGSystem(PGSystemPrototype):
  def __init__(self, x, y, z, name, sector, uncertainty):
    super(PGSystem, self).__init__(x, y, z, name, sector, uncertainty)

  def __repr__(self):
    return u"PGSystem({})".format(self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y, self.position.z))


class KnownSystem(System):
  def __init__(self, obj):
    super(KnownSystem, self).__init__(float(obj['x']), float(obj['y']), float(obj['z']), obj['name'], obj['id64'])
    self._id = obj['id'] if 'id' in obj else None
    self._needs_permit = obj['needs_permit'] if 'needs_permit' in obj else False
    self._allegiance = obj['allegiance'] if 'allegiance' in obj else None

  @property
  def needs_permit(self):
    return self._needs_permit

  @property
  def allegiance(self):
    return self._allegiance

  def __repr__(self):
    return u"KnownSystem({0})".format(self.name)

  def __eq__(self, other):
    if isinstance(other, KnownSystem):
      return ((self.id is None or other.id is None or self.id == other.id) and self.name == other.name and self.position == other.position)
    elif isinstance(other, System):
      return super(KnownSystem, self).__eq__(other)
    else:
      return NotImplemented

  def __hash__(self):
    return super(KnownSystem, self).__hash__()


    
#
# System ID calculations
#

def mask_id64_as_system(input):
  result = input
  if util.is_str(input):
    result = int(result, 16)
  result &= (2**55) - 1
  if util.is_str(input):
    result = '{0:016X}'.format(result)
  return result


def mask_id64_as_body(input):
  result = input
  if util.is_str(input):
    result = int(result, 16)
  result >>= 55
  result &= (2**9)-1
  if util.is_str(input):
    result = '{0:X}'.format(result)
  return result


def calculate_from_id64(input):
  # If input is a string, assume hex
  if util.is_str(input):
    input = int(input, 16)
  # Calculate the shifts we need to do to get the individual fields out
  # Can't tell how long N2 field is (or if the start moves!), assuming ~16 for now
  len_used = 0
  input, mc       = util.unpack_and_shift(input, 3);    len_used += 3    # mc = 0-7 for a-h
  input, boxel_z  = util.unpack_and_shift(input, 7-mc); len_used += 7-mc
  input, sector_z = util.unpack_and_shift(input, 7);    len_used += 7
  input, boxel_y  = util.unpack_and_shift(input, 7-mc); len_used += 7-mc
  input, sector_y = util.unpack_and_shift(input, 6);    len_used += 6
  input, boxel_x  = util.unpack_and_shift(input, 7-mc); len_used += 7-mc
  input, sector_x = util.unpack_and_shift(input, 7);    len_used += 7
  input, n2       = util.unpack_and_shift(input, 55-len_used)
  input, body_id  = util.unpack_and_shift(input, 9)
  # Multiply each X/Y/Z value by the cube width to get actual coords
  boxel_size = 10 * (2**mc)
  coord_x = (sector_x * sector.sector_size) + (boxel_x * boxel_size) + (boxel_size / 2)
  coord_y = (sector_y * sector.sector_size) + (boxel_y * boxel_size) + (boxel_size / 2)
  coord_z = (sector_z * sector.sector_size) + (boxel_z * boxel_size) + (boxel_size / 2)
  coords_internal = vector3.Vector3(coord_x, coord_y, coord_z)
  # Shift the coords to be the origin we know and love
  coords = coords_internal + sector.internal_origin_offset
  return (coords, boxel_size, n2, body_id)


def calculate_id64(pos, mcode, n2):
  # Get the data we need to start with (mc as 0-7, cube width, boxel X/Y/Z coords)
  mc = ord(sector.get_mcode(mcode)) - ord('a')
  cube_width = sector.get_mcode_cube_width(mcode)
  boxel_coords = (pgnames.get_boxel_origin(pos, mcode) - sector.internal_origin_offset) / cube_width
  # Populate each field, shifting as required
  output = util.pack_and_shift(0, 0, 3)
  output = util.pack_and_shift(output, int(n2), 16)  # Not sure what the length is
  output = util.pack_and_shift(output, int(boxel_coords.x), 14-mc)
  output = util.pack_and_shift(output, int(boxel_coords.y), 13-mc)
  output = util.pack_and_shift(output, int(boxel_coords.z), 14-mc)
  output = util.pack_and_shift(output, mc, 3)
  return output

