import argparse
import collections
import logging
import math
import random
import re
import vector3
import station
import system_internal as system
import util

log = logging.getLogger("filter")

default_direction_angle = 15.0

entry_separator = ';'
entry_subseparator = ','
entry_kvseparator_re = re.compile('(=|!=|<>|<|>|<=|>=)')


class AnyType(object):
  def __str__(self):
    return "Any"
  def __repr__(self):
    return "Any"
Any = AnyType()

class PosArgsType(object):
  def __str__(self):
    return "PosArgs"
  def __repr__(self):
    return "PosArgs"
PosArgs = PosArgsType()

class Operator(object):
  def __init__(self, op, value):
    self.value = value
    self.operator = op
  def __str__(self):
    return "{} {}".format(self.operator, self.value)
  def __repr__(self):
    return "{} {}".format(self.operator, self.value)

_assumed_operators = {int: '<', float: '<'}


def _get_valid_ops(fn):
  if isinstance(fn, dict) and 'fn' in fn:
    return _get_valid_ops(fn['fn'])
  if fn is int or fn is float:
    return ['=','<','>','<=','>=']
  if isinstance(fn, dict):
    return ['=']
  else:
    return ['=','!=','<>']

def _get_valid_conversion(fndict, idx, subidx = None):
  if idx in fndict:
    if isinstance(fndict[idx], dict) and 'fn' in fndict[idx]:
      return fndict[idx]['fn']
    else:
      return fndict[idx]
  if idx is None:
    if subidx is not None and subidx in fndict:
      return fndict[subidx]
    elif PosArgs in fndict:
      return fndict[PosArgs]
  return None

_conversions = {
  'sc_distance': {
                   'max': None,
                   'special': [Any],
                   'fn': int
                 },
  'pad':         {
                   'max': 1,
                   'special': [Any, None],
                   'fn': str.upper
                 },
  'close_to':    {
                   'max': None,
                   'special': [],
                   'fn':
                   {
                     PosArgs: 'system',
                     'distance':  {'max': None, 'special': [], 'fn': float},
                     'direction': {'max': None, 'special': [], 'fn': 'system'},
                     'angle':     {'max': None, 'special': [], 'fn': float}
                   }
                 },
  'allegiance':  {
                   'max': 1,
                   'special': [Any, None],
                   'fn': str
                 },
  'limit':       {
                   'max': 1,
                   'special': [],
                   'fn': int
                 },
}


def _global_conv(val, specials = []):
  if isinstance(val, Operator):
    return Operator(value=_global_conv(val.value, specials), op=val.operator)

  if val.lower() == "any" and Any in specials:
    return (Any, False)
  elif val.lower() == "none" and None in specials:
    return (None, False)
  else:
    return (val, True)


def parse_filter_string(s, extra_converters = {}):
  entries = s.split(entry_separator)
  output = {}
  # For each separate filter entry...
  for entry in entries:
    ksv = entry_kvseparator_re.split(entry, 1)
    key = ksv[0].strip()
    if key in _conversions:
      multiple = (_conversions[key]['max'] != 1)
    else:
      raise KeyError("Unexpected filter key provided: {0}".format(key))
    ksvlist = ksv[2].strip().split(entry_subseparator)
    # Do we have sub-entries, or just a simple key=value ?
    value = {}
    # For each sub-entry...
    for e in ksvlist:
      eksv = [s.strip() for s in entry_kvseparator_re.split(e, 1)]
      # Is this sub-part a subkey=value?
      if len(eksv) > 1:
        if eksv[0] not in value:
          value[eksv[0]] = []
        value[eksv[0]].append(Operator(value=eksv[2], op=eksv[1]))
      else:
        # If not, give it a position-based index
        if PosArgs not in value:
          value[PosArgs] = []
        value[PosArgs].append(Operator(value=eksv[0], op=ksv[1]))
    # Set the value and move on
    if key not in output:
      output[key] = []
    output[key].append(value)

  # For each result
  for k in output.keys():
    # Do we know about it?
    if k in _conversions:
      if _conversions[k]['max'] not in [None, 1] and len(output[k]) > _conversions[k]['max']:
        raise KeyError("Filter key {} provided more than its maximum {} times".format(k, _conversions[k]['max']))
      # Is it a complicated one, or a simple key=value?
      if isinstance(_conversions[k]['fn'], dict):
        # For each present subkey, check if we know about it
        outlist = output[k]
        # For each subkey...
        for outentry in outlist:
          # For each named entry in that subkey (and None for positional args)...
          for ek in outentry:
            # For each instance of that named entry...
            for i in range(0, len(outentry[ek])):
              ev = outentry[ek][i]
              # Check we have a valid conversion for the provided name
              conv = _get_valid_conversion(_conversions[k]['fn'], ek, i)
              if not conv:
                raise KeyError("Unexpected filter subkey provided: {0}".format(ek))
              # Check the provided operator is valid in this scenario
              if ev.operator not in _get_valid_ops(conv):
                raise KeyError("Invalid operator provided for filter subkey '{}/{}'".format(k, ek))
              # Do the conversions
              specials = _conversions[k]['fn'][ek]['special'] if (ek in _conversions[k]['fn'] and isinstance(_conversions[k]['fn'][ek], dict)) else []
              ev.value, continue_conv = _global_conv(ev.value, specials)
              if continue_conv:
                if util.is_str(conv):
                  if conv in extra_converters:
                    ev.value = extra_converters[conv](ev.value)
                  else:
                    raise ValueError("Could not perform conversion for filter subkey '{}/{}' with custom converter '{}'".format(k, ek, conv))
                else:
                  ev.value = conv(ev.value)
      else:
        # For each entry associated with this key...
        for ovl in output[k]:
          # For each entry in the positional args list...
          for ov in ovl[PosArgs]:
            # Check the provided operator is valid in this scenario
            if ov.operator not in _get_valid_ops(_conversions[k]['fn']):
              raise KeyError("Invalid operator provided for filter key '{}'".format(k))
            # Do the conversions
            ov.value, continue_conv = _global_conv(ov.value, _conversions[k]['special'])
            if continue_conv:
              if util.is_str(_conversions[k]['fn']):
                if _conversions[k]['fn'] in extra_converters:
                  ov.value = extra_converters[_conversions[k]['fn']](ov.value)
                else:
                  raise ValueError("Could not perform conversion for special converter '{}'".format(_conversions[k]['fn']))
              else:
                ov.value = _conversions[k]['fn'](ov.value)
    else:
      raise KeyError("Unexpected filter key provided: {0}".format(k))

  return output


def normalise_filter_object(filters, strip_unexpected = False, anonymous_posargs = True, assume_ops = True):
  if not isinstance(filters, dict):
    raise ValueError("filter object must be a dict")
  output = filters
  for k in output:
    # Check we know about this key
    if k not in _conversions:
      if strip_unexpected:
        del output[k]
        continue
      else:
        raise ValueError("unexpected filter key '{}'".format(k))
    # Check the value is a list
    if not isinstance(output[k], list):
      output[k] = [output[k]]
    convdata = _conversions[k]
    # Check it hasn't been specified too many times
    if convdata['max'] is not None and len(output[k]) > convdata['max']:
      raise ValueError("filter key '{}' specified {} times, more than its maximum allowed {} times".format(k, len(output[k]), convdata['max']))
    # Start checking inner stuff
    for i in range(0, len(output[k])):
      if not isinstance(output[k][i], dict):
        if anonymous_posargs:
          output[k][i] = {PosArgs: output[k][i]}
        else:
          raise ValueError("filter key '{}' contains invalid value".format(k))
      for ek in output[k][i]:
        if not isinstance(output[k][i][ek], list):
          output[k][i][ek] = [output[k][i][ek]]
        # Ensure we have a relevant item in the convdata
        if ek is PosArgs:
          # If we're not simple data, we should either have a PosArgs entry or specific numeric entries
          if isinstance(convdata['fn'], dict):
            if ek not in convdata['fn'] and len(output[k][i][ek])-1 not in convdata['fn']:
              raise ValueError("filter key '{}' contains unexpected positional arguments".format(k))
            if ek in convdata['fn'] and convdata['fn'][ek]['max'] is not None and len(output[k][i][ek]) > convdata['fn'][ek]['max']:
              raise ValueError("filter key '{}' contains too many positional arguments".format(k))
        else:
          if not isinstance(convdata['fn'], dict):
            raise ValueError("filter key '{}' contains complex data with subkey '{}' when it should not".format(k, ek))
          if ek not in convdata['fn']:
            raise ValueError("filter key '{}' contains unexpected subkey '{}'".format(k, ek))
        for j in range(0, len(output[k][i][ek])):
          if not isinstance(output[k][i][ek][j], Operator):
            if assume_ops:
              conv_fn = convdata['fn']
              if isinstance(conv_fn, dict):
                conv_fn = conv_fn[ek]
              if isinstance(conv_fn, dict):
                conv_fn = conv_fn['fn']
              output[k][i][ek][j] = Operator(_assumed_operators.get(conv_fn, '='), output[k][i][ek][j])
            else:
              raise ValueError("filter key '{}/{}' was not an Operator object".format(k, ek))
  return output


def generate_filter_sql(filters):
  select_str = []
  filter_str = []
  group_str = []
  order_str = []
  limit = None
  select_params = []
  filter_params = []
  group_params = []
  order_params = []
  req_tables = set()
  idx = 0

  if 'close_to' in filters:
    start_idx = idx
    req_tables.add('systems')
    for oentry in filters['close_to']:
      for entry in oentry[PosArgs]:
        pos = entry.value.position
        select_str.append("(((? - systems.pos_x) * (? - systems.pos_x)) + ((? - systems.pos_y) * (? - systems.pos_y)) + ((? - systems.pos_z) * (? - systems.pos_z))) AS diff{0}".format(idx))
        select_params += [pos.x, pos.x, pos.y, pos.y, pos.z, pos.z]
        # For each operator and value...
        if 'distance' in oentry:
          for opval in oentry['distance']:
            filter_str.append("diff{} {} ? * ?".format(idx, opval.operator))
            filter_params += [opval.value, opval.value]
        idx += 1
        if 'direction' in oentry:
          for dentry in oentry['direction']:
            dpos = dentry.value.position
            select_str.append("vec3_angle(systems.pos_x-?,systems.pos_y-?,systems.pos_z-?,?-?,?-?,?-?) AS diff{}".format(idx))
            select_params += [pos.x, pos.y, pos.z, dpos.x, pos.x, dpos.y, pos.y, dpos.z, pos.z]
            if 'angle' in oentry:
              for aentry in oentry['angle']:
                angle = aentry.value * math.pi / 180.0
                filter_str.append("diff{} {} ?".format(idx, aentry.operator))
                filter_params.append(angle)
            idx += 1
    order_str.append("+".join(["diff{}".format(i) for i in range(start_idx, idx)]))
  if 'allegiance' in filters:
    req_tables.add('systems')
    for oentry in filters['allegiance']:
      for entry in oentry[PosArgs]:
        if (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          filter_str.append("(systems.allegiance IS NOT NULL AND systems.allegiance != 'None')")
        elif (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          filter_str.append("(systems.allegiance IS NULL OR systems.allegiance == 'None')")
        else:
          extra_str = " OR systems.allegiance IS NULL OR systems.allegiance == 'None'"
          filter_str.append("(systems.allegiance {} ?{})".format(entry.operator, extra_str if entry.operator == '!=' else ''))
          filter_params.append(entry.value)
  if 'pad' in filters:
    req_tables.add('stations')
    for oentry in filters['pad']:
      for entry in oentry[PosArgs]:
        if (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          filter_str.append("stations.max_pad_size IS NULL")
        elif (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          filter_str.append("stations.max_pad_size IS NOT NULL")
        else:
          extra_str = " OR stations.max_pad_size IS NULL"
          filter_str.append("stations.max_pad_size {} ?{}".format(entry.operator, extra_str if entry.operator == '!=' else ''))
          filter_params.append(entry.value)
  if 'sc_distance' in filters:
    req_tables.add('stations')
    for oentry in filters['sc_distance']:
      for entry in oentry[PosArgs]:
        filter_str.append("stations.sc_distance {} ?".format(entry.operator))
        filter_params.append(entry.value)
    order_str.append("stations.sc_distance")
  if 'limit' in filters:
    limit = int(filters['limit'])

  return {
    'select': (select_str, select_params),
    'filter': (filter_str, filter_params),
    'order': (order_str, order_params),
    'group': (group_str, group_params),
    'limit': limit,
    'tables': list(req_tables)
  }


def filter_list(s_list, filters, limit = None, p_src_list = None):
  src_list = None
  if p_src_list is not None:
    src_list = [s if isinstance(s, station.Station) else station.Station.none(s) for s in p_src_list]

  if (src_list is not None and 'direction' in filters):
    direction_obj = filters['direction']
    direction_angle = filters['direction_angle'] if 'direction_angle' in filters else default_direction_angle
    max_angle = direction_angle * math.pi / 180.0
    if direction_obj is None:
      log.error("Could not find direction target \"{0}\"!".format(self.args.direction))
      return

  asys = []
  maxdist = 0.0

  for s in s_list:
    if isinstance(s, station.Station):
      st = s
      sy = s.system
    elif isinstance(s, system.KnownSystem):
      st = station.Station.none(s)
      sy = s
    else:
      log.error("Object of type '{}' cannot be filtered with systems/stations".format(type(s)))
      continue

    if ('allegiance' in filters and ((not hasattr(sy, 'allegiance')) or filters['allegiance'] != sy.allegiance)):
      continue

    has_stns = (hasattr(sy, 'allegiance') and sy.allegiance is not None)
    
    if ('pad' in filters and not has_stns):
      continue

    if ('direction' in filters and src_list is not None and not self.all_angles_within(src_list, sy, direction_obj, max_angle)):
      continue

    if ('pad' in filters and filters['pad'] != 'L' and st.max_pad_size == 'L'):
      continue

    if ('min_sc_distance' in filters and (st.distance is None or st.distance < filters['min_sc_distance'])):
      continue
    if ('max_sc_distance' in filters and (st.distance is None or st.distance > filters['max_sc_distance'])):
      continue

    dist = None
    if src_list is not None:
      dist = math.fsum([s.distance_to(start) for start in src_list])

      if ('min_distance' in filters and any([s.distance_to(start) < filters['min_distance'] for start in src_list])):
        continue
      if ('max_distance' in filters and any([s.distance_to(start) > filters['max_distance'] for start in src_list])):
        continue

    if limit is None or len(asys) < limit or (dist is None or dist < maxdist):
      # We have a new contender; add it, sort by distance, chop to length and set the new max distance
      asys.append(s)
      # Sort the list by distance to ALL start systems
      if src_list is not None:
        asys.sort(key=lambda t: math.fsum([t.distance_to(start) for start in src_list]))

      if limit is not None:
        asys = asys[0:limit]
      maxdist = max(dist, maxdist)

  return asys


def all_angles_within(starts, dest1, dest2, max_angle):
  for d in starts:
    cur_dir = (dest1.position - d.position)
    test_dir = (dest2.position - d.position)
    if cur_dir.angle_to(test_dir) > max_angle:
      return False
  return True
