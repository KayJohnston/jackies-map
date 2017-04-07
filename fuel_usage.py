#!/usr/bin/env python

from __future__ import print_function
import argparse
import calc
import env
import logging
from math import log10, floor, fabs
import sys
import ship

app_name = "fuel_usage"

log = logging.getLogger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Plot jump distance matrix", fromfile_prefix_chars="@", parents = ap_parents, prog = app_name)
    ap.add_argument("-f", "--fsd", type=str, required=('ship' not in state), help="The ship's frame shift drive in the form 'A6 or '6A'")
    ap.add_argument("-m", "--mass", type=float, required=('ship' not in state), help="The ship's unladen mass excluding fuel")
    ap.add_argument("-t", "--tank", type=float, required=('ship' not in state), help="The ship's fuel tank size")
    ap.add_argument("-s", "--starting-fuel", type=float, required=False, help="The starting fuel quantity (default: tank size)")
    ap.add_argument("-c", "--cargo", type=int, default=0, help="Cargo on board the ship")
    ap.add_argument("-r", "--refuel", action='store_true', default=False, help="Assume that the ship can be refueled as needed, e.g. by fuel scooping")
    ap.add_argument("systems", metavar="system", nargs='+', help="Systems")

    self.args = ap.parse_args(arg)

    if self.args.fsd is not None and self.args.mass is not None and self.args.tank is not None:
      self.ship = ship.Ship(self.args.fsd, self.args.mass, self.args.tank)
    elif 'ship' in state:
      fsd = self.args.fsd if self.args.fsd is not None else state['ship'].fsd
      mass = self.args.mass if self.args.mass is not None else state['ship'].mass
      tank = self.args.tank if self.args.tank is not None else state['ship'].tank_size
      self.ship = ship.Ship(fsd, mass, tank)
    else:
      log.error("Error: You must specify all of --fsd, --mass and --tank, or have previously set these")
      sys.exit(1)

    if self.args.starting_fuel is None:
      self.args.starting_fuel = self.ship.tank_size

  def run(self):
    with env.use() as envdata:
      systems = envdata.parse_systems(self.args.systems)
      for y in self.args.systems:
        if y not in systems or systems[y] is None:
          log.error("Could not find system \"{0}\"!".format(y))
          return

    cur_fuel = self.args.starting_fuel
    output_data = [{'src': systems[self.args.systems[0]]}]

    prev = None
    for s in systems.values():
      if prev is None:
        # First iteration
        prev = s
        continue
      distance = prev.distance_to(s)
      is_long = False
      is_ok = True
      if self.args.refuel:
        fmax = self.ship.max_fuel_weight(distance, allow_invalid=True)
        # Fudge factor to prevent cost coming out at exactly maxfuel (stupid floating point!)
        cur_fuel = min(fmax - 0.000001, self.ship.tank_size)
        is_long = (fmax >= 0.0 and fmax < self.ship.tank_size)
        is_ok = (is_ok and fmax >= 0.0)

      fuel_cost = self.ship.cost(distance, cur_fuel, self.args.cargo)
      cur_fuel -= fuel_cost
      is_ok = (is_ok and fuel_cost <= self.ship.fsd.maxfuel and cur_fuel >= 0.0)
      output_data.append({
          'src': prev, 'dst': s,
          'distance': distance, 'cost': fuel_cost,
          'remaining': cur_fuel, 'ok': is_ok, 'long': is_long})

    d_max_len = 1.0
    c_max_len = 1.0
    f_max_len = 1.0
    f_min_len = 1.0
    for i in range(1, len(output_data)):
      od = output_data[i]
      d_max_len = max(d_max_len, od['distance'])
      c_max_len = max(c_max_len, od['cost'])
      f_max_len = max(f_max_len, od['remaining'])
      f_min_len = min(f_min_len, od['remaining'])
    # Length = "NNN.nn", so length = len(NNN) + 3 = log10(NNN) + 4
    d_max_len = str(int(floor(log10(fabs(d_max_len)))) + 4)
    c_max_len = str(int(floor(log10(fabs(c_max_len)))) + 4)
    f_max_len = int(floor(log10(fabs(f_max_len)))) + 4
    f_min_len = int(floor(abs(log10(fabs(f_min_len))))) + (5 if f_min_len < 0.0 else 4)
    f_len = str(max(f_max_len, f_min_len))

    print('')
    print(output_data[0]['src'].to_string())
    for i in range(1, len(output_data)):
      leg = output_data[i]
      dist = leg['src'].distance_to(leg['dst'])
      print(('    ={4}= {0: >'+d_max_len+'.2f}Ly / {1:>'+c_max_len+'.2f}T / {2:>'+f_len+'.2f}T ={4}=> {3}').format(
            dist,
            leg['cost'],
            leg['remaining'],
            leg['dst'].to_string(),
            _get_leg_char(leg)))
    print('')


def _get_leg_char(leg):
  if leg['ok']:
    if leg['long']:
      return '~'
    else:
      return '='
  else:
    return '!'

if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
