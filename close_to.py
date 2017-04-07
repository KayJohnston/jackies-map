#!/usr/bin/env python

from __future__ import print_function
import argparse
import env
import filter
import logging
import math
import sys

app_name = "close_to"

log = logging.getLogger(app_name)

default_max_angle = 15.0


class ApplicationAction(argparse.Action):
  def __call__(self, parser, namespace, value, option_strings=None):
    n = vars(namespace)
    system_list = n['system'] if n['system'] is not None else []
    need_new = True
    i = 0
    while i < len(system_list):
      if self.dest not in system_list[i]:
        need_new = False
        break
      i += 1
    if need_new:
      system_list.append({})
    d = system_list[i]
    if self.dest == 'system':
      d['system'] = value[0]
    else:
      d[self.dest] = value
      setattr(namespace, self.dest, value)
    setattr(namespace, 'system', system_list)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Find Nearby Systems", fromfile_prefix_chars="@", parents = ap_parents, prog = app_name)
    ap.add_argument("-n", "--num", type=int, required=False, default=10, help="Show the specified number of nearby systems")
    ap.add_argument("-d", "--min-dist", type=float, required=False, action=ApplicationAction, help="Exclude systems less than this distance from reference")
    ap.add_argument("-m", "--max-dist", type=float, required=False, action=ApplicationAction, help="Exclude systems further this distance from reference")
    ap.add_argument("-a", "--allegiance", type=str, required=False, default=None, help="Only show systems with the specified allegiance")
    ap.add_argument("-s", "--max-sc-distance", type=float, required=False, help="Only show systems with a starport less than this distance from entry point")
    ap.add_argument("-p", "--pad-size", required=False, type=str.upper, choices=['S','M','L'], help="Only show systems with stations matching the specified pad size")
    ap.add_argument("-l", "--list-stations", default=False, action='store_true', help="List stations in returned systems")
    ap.add_argument("--direction", type=str, required=False, help="A system or set of coordinates that returned systems must be in the same direction as")
    ap.add_argument("--direction-angle", type=float, required=False, default=default_max_angle, help="The maximum angle, in degrees, allowed for the direction check")

    ap.add_argument("system", metavar="system", nargs=1, action=ApplicationAction, help="The system to find other systems near")

    remaining = arg
    args = argparse.Namespace()
    while remaining:
      args, remaining = ap.parse_known_args(remaining, namespace=args)
      self.args = args
    if not hasattr(self, 'args'):
      self.args = ap.parse_args(arg)

  def run(self):
    with env.use() as envdata:
      # Add the system object to each system arg
      tmpsystems = envdata.parse_systems([d['system'] for d in self.args.system])
      for d in self.args.system:
        d['sysobj'] = tmpsystems.get(d['system'], None)
        if d['sysobj'] is None:
          log.error("Could not find start system \"{0}\"!".format(d['system']))
          return
      # Create a list of names for quick checking in the main loop
      start_names = [d['system'].lower() for d in self.args.system]

      if self.args.direction is not None:
        direction_obj = envdata.parse_system(self.args.direction)
        if direction_obj is None:
          log.error("Could not find direction system \"{0}\"!".format(self.args.direction))
          return

    asys = []

    close_to_list = []
    for s in self.args.system:
      min_dist = [filter.Operator('>=', s['min_dist'])] if 'min_dist' in s else []
      max_dist = [filter.Operator('<',  s['max_dist'])] if 'max_dist' in s else []
      close_to_list.append({filter.PosArgs: [filter.Operator('=', s['sysobj'])], 'distance': min_dist + max_dist})
    if not any([('max_dist' in s) for s in self.args.system]):
      log.warning("database query will be slow unless at least one reference system has a max distance specified with --max-dist")

    filters = {}
    filters['close_to'] = close_to_list
    if self.args.pad_size is not None:
      # Retain previous behaviour: 'M' counts as 'any'
      filters['pad'] = [{filter.PosArgs: [filter.Operator('=', 'L' if self.args.pad_size == 'L' else filter.Any)]}]
    if self.args.max_sc_distance is not None:
      filters['sc_distance'] = [{filter.PosArgs: [filter.Operator('<', self.args.max_sc_distance)]}]
    if self.args.allegiance is not None:
      filters['allegiance'] = [{filter.PosArgs: [filter.Operator('=', self.args.allegiance)]}]
    if self.args.num is not None:
      # Get extras, in case we get our reference systems as a result
      filters['limit'] = self.args.num + len(self.args.system)
    if self.args.direction is not None:
      for entry in filters['close_to']:
        entry['direction'] = [filter.Operator('=', direction_obj)]
        entry['angle'] = [filter.Operator('<', self.args.direction_angle)]

    with env.use() as envdata:
      # Filter out our reference systems from the results
      names = [d['sysobj'].name for d in self.args.system]
      asys = [s for s in envdata.find_all_systems(filters=filters) if s.name not in names]
      if self.args.num:
        asys = asys[0:self.args.num]

      if not len(asys):
        print("")
        print("No matching systems")
        print("")
      else:
        print("")
        print("Matching systems close to {0}:".format(', '.join([d["sysobj"].name for d in self.args.system])))
        print("")
        for i in range(0, len(asys)):
          if len(self.args.system) == 1:
            print("    {0} ({1:.2f}Ly)".format(asys[i].name, asys[i].distance_to(self.args.system[0]['sysobj'])))
          else:
            print("    {0}".format(asys[i].name, " ({0:.2f}Ly)".format(asys[i].distance_to(self.args.system[0]['sysobj']))))
          if self.args.list_stations:
            stlist = envdata.find_stations(asys[i])
            stlist.sort(key=lambda t: t.distance)
            for stn in stlist:
              print("        {0}".format(stn.to_string(False)))
        print("")
        if len(self.args.system) > 1:
          for d in self.args.system:
            print("  Distance from {0}:".format(d['system']))
            print("")
            asys.sort(key=lambda t: t.distance_to(d['sysobj']))
            for i in range(0, len(asys)):
              # Print distance from the current candidate system to the current start system
              print("    {0} ({1:.2f}Ly)".format(asys[i].name, asys[i].distance_to(d['sysobj'])))
            print("")

  def all_angles_within(self, starts, dest1, dest2, max_angle):
    for d in starts:
      cur_dir = (dest1.position - d['sysobj'].position)
      test_dir = (dest2.position - d['sysobj'].position)
      if cur_dir.angle_to(test_dir) > max_angle:
        return False
    return True


if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
  env.stop()
