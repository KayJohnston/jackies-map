#!/usr/bin/env python

from __future__ import print_function
import argparse
import calc
import env
import logging
import math
import sys

app_name = "distance"

log = logging.getLogger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Plot jump distance matrix", fromfile_prefix_chars="@", parents = ap_parents, prog = app_name)
    ap.add_argument("-c", "--csv", action='store_true', default=False, help="Output in CSV")
    ap.add_argument("-o", "--ordered", action='store_true', default=False, help="List is ordered (do not sort alphabetically)")
    ap.add_argument("-f", "--full-width", action='store_true', default=False, help="Do not truncate heading names for readability")
    ap.add_argument("-s", "--start", type=str, required=False, help="Defines a start system to calculate all other distances from")
    ap.add_argument("-r", "--route", action='store_true', default=False, help="List of systems is a sequential list to visit and get distances between")
    ap.add_argument("systems", metavar="system", nargs='+', help="Systems")

    self.args = ap.parse_args(arg)
    self.longest = 6
    self._max_heading = 1000 if self.args.full_width else 10
    self._padding_width = 2

    self._calc = calc.Calc()

  def print_system(self, name, is_line_start, max_len = None):
    if self.args.csv:
      sys.stdout.write('%s%s' % ('' if is_line_start else ',', name))
    else:
      # If name length is > max, truncate name and append ".."
      tname = name if (max_len is None or len(name) <= max_len) else (name[0:max_len-2] + '..')
      # If we have a max length, account for it when working out padding
      pad = (min(self.longest, max_len) if max_len is not None else self.longest) + self._padding_width - len(tname)
      sys.stdout.write('%s%s' % (' ' * pad, tname))

  def format_distance(self, dist):
    fmt = '{0:.2f}' if self.args.csv else '{0: >7.2f}'
    return fmt.format(dist)

  def run(self):
    if not self.args.csv:
      self.longest = max([len(s) for s in self.args.systems])

    with env.use() as envdata:
      start_obj = None
      if self.args.start is not None:
        start_obj = envdata.parse_system(self.args.start)
        if start_obj is None:
          log.error("Could not find start system \"{0}\"!".format(self.args.start))
          return

      systems = envdata.parse_systems(self.args.systems)
      for y in self.args.systems:
        if y not in systems or systems[y] is None:
          log.error("Could not find system \"{0}\"!".format(y))
          return

    print('')

    if self.args.route:
      distances = []
      d_max_len = 1.0
      for i in range(1, len(self.args.systems)):
        sobj1 = systems[self.args.systems[i-1]]
        sobj2 = systems[self.args.systems[i]]
        distances.append(sobj1.distance_to(sobj2))
        d_max_len = max(d_max_len, distances[-1])

      d_max_len = str(int(math.floor(math.log10(d_max_len))) + 4)
      if len(self.args.systems) > 0:
        print(systems[self.args.systems[0]].to_string())
      for i in range(1, len(self.args.systems)):
        print(('  === {0: >'+d_max_len+'.2f}Ly ===> {1}').format(distances[i-1], systems[self.args.systems[i]].to_string()))

    elif self.args.start is not None and start_obj is not None:
      distances = {}
      d_max_len = 1.0
      for s in self.args.systems:
        distances[s] = systems[s].distance_to(start_obj)
        d_max_len = max(d_max_len, distances[s])

      if not self.args.ordered:
        self.args.systems.sort(key=distances.get)

      d_max_len = str(int(math.floor(math.log10(d_max_len))) + 4)
      for s in self.args.systems:
        sobj = systems[s]
        print((' {0} === {1: >'+d_max_len+'.2f}Ly ===> {2}').format(start_obj.to_string(), sobj.distance_to(start_obj), sobj.to_string()))

    else:
      # If we have many systems, generate a Raikogram
      if len(self.args.systems) > 2 or self.args.csv:

        if not self.args.ordered:
          # Remove duplicates
          seen = set()
          seen_add = seen.add
          self.args.systems = [x for x in self.args.systems if not (x in seen or seen_add(x))]
          # Sort alphabetically
          self.args.systems.sort()

        if not self.args.csv:
          self.print_system('', True)

        for y in self.args.systems:
          self.print_system(y, False, self._max_heading)
        print('')

        for x in self.args.systems:
          self.print_system(x, True)
          for y in self.args.systems:
            self.print_system('-' if y == x else self.format_distance(systems[x].distance_to(systems[y])), False, self._max_heading)
          print('')

        if self.args.ordered:
          print('')
          self.print_system('Total:', True)
          total_dist = self._calc.route_dist([systems[x] for x in self.args.systems])
          self.print_system(self.format_distance(total_dist), False, self._max_heading)

        print('')

      # Otherwise, just return the simple output
      elif len(self.args.systems) > 1:
        start = systems[self.args.systems[0]]
        end = systems[self.args.systems[1]]

        print(start.to_string())
        print('    === {0: >7.2f}Ly ===> {1}'.format(start.distance_to(end), end.to_string()))
      else:
        log.error("For a simple distance calculation, at least two system names must be provided!")
        return
    print('')

if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
