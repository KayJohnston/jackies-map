#!/usr/bin/env python

from __future__ import print_function
import argparse
import logging
import math
import sys
import env
import calc as c
import ship
import routing as rx
import util
import solver
from station import Station
from fsd import FSD

app_name = "edts"

log = logging.getLogger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Elite: Dangerous TSP Solver", fromfile_prefix_chars="@", parents=ap_parents, prog = app_name)
    ap.add_argument("-f", "--fsd", type=str, required=False, help="The ship's frame shift drive in the form 'A6 or '6A'")
    ap.add_argument("-m", "--mass", type=float, required=False, help="The ship's unladen mass excluding fuel")
    ap.add_argument("-t", "--tank", type=float, required=False, help="The ship's fuel tank size")
    ap.add_argument("-c", "--cargo", type=int, default=0, help="Cargo to collect at each station")
    ap.add_argument("-j", "--jump-range", type=float, required=False, help="The ship's max jump range with full fuel and empty cargo")
    ap.add_argument("-w", "--witchspace-time", type=int, default=c.default_ws_time, help="Time in seconds spent in hyperspace jump")
    ap.add_argument("-s", "--start", type=str, required=True, help="The starting station, in the form 'system/station' or 'system'")
    ap.add_argument("-e", "--end", type=str, required=True, help="The end station, in the form 'system/station' or 'system'")
    ap.add_argument("-n", "--num-jumps", default=None, type=int, help="The number of stations to visit, not including the start/end")
    ap.add_argument("-p", "--pad-size", default="M", type=str.upper, choices=['S','M','L'], help="The landing pad size of the ship (S/M/L)")
    ap.add_argument("-d", "--jump-decay", type=float, default=0.0, help="An estimate of the range decay per jump in Ly (e.g. due to taking on cargo)")
    ap.add_argument("-r", "--route", default=False, action='store_true', help="Whether to try to produce a full route rather than just legs")
    ap.add_argument("-o", "--ordered", default=False, action='store_true', help="Whether the stations are already in a set order")
    ap.add_argument("-l", "--long-jumps", default=False, action='store_true', help="Whether to allow for jumps only possible at low fuel when routing")
    ap.add_argument("-a", "--accurate", dest='route_strategy', action='store_const', const='trunkle', default=c.default_strategy, help="Use a more accurate but slower routing method (equivalent to --route-strategy=trunkle)")
    ap.add_argument("--format", default='long', type=str.lower, choices=['long','summary','short','csv'], help="The format to display the output in")
    ap.add_argument("--reverse", default=False, action='store_true', help="Whether to reverse the generated route")
    ap.add_argument("--jump-time", type=float, default=c.default_jump_time, help="Seconds taken per hyperspace jump")
    ap.add_argument("--diff-limit", type=float, default=1.5, help="The multiplier of the fastest route which a route must be over to be discounted")
    ap.add_argument("--slf", type=float, default=c.default_slf, help="The multiplier to apply to multi-jump legs to account for imperfect system positions")
    ap.add_argument("--route-strategy", default=c.default_strategy, help="The strategy to use for route plotting. Valid options are 'trundle', 'trunkle' and 'astar'")
    ap.add_argument("--rbuffer", type=float, default=rx.default_rbuffer_ly, help="A minimum buffer distance, in Ly, used to search for valid stars for routing")
    ap.add_argument("--hbuffer", type=float, default=rx.default_hbuffer_ly, help="A minimum buffer distance, in Ly, used to search for valid next legs. Not used by the 'astar' strategy.")
    ap.add_argument("--solve-mode", type=str, default=solver.CLUSTERED, choices=solver.modes, help="The mode used by the travelling salesman solver")
    ap.add_argument("stations", metavar="system[/station]", nargs="*", help="A station to travel via, in the form 'system/station' or 'system'")
    self.args = ap.parse_args(arg)

    # If the user hasn't provided a number of stops to use, assume we're stopping at all provided
    if self.args.num_jumps is None:
      self.args.num_jumps = len(self.args.stations)

    if self.args.fsd is not None and self.args.mass is not None and self.args.tank is not None:
      # If user has provided full ship data in this invocation, use it
      # TODO: support cargo capacity?
      self.ship = ship.Ship(self.args.fsd, self.args.mass, self.args.tank)
    elif 'ship' in state:
      # If we have a cached ship, use that (with any overrides provided as part of this invocation)
      fsd = self.args.fsd if self.args.fsd is not None else state['ship'].fsd
      mass = self.args.mass if self.args.mass is not None else state['ship'].mass
      tank = self.args.tank if self.args.tank is not None else state['ship'].tank_size
      self.ship = ship.Ship(fsd, mass, tank)
    else:
      # No ship is fine as long as we have a static jump range set
      if self.args.jump_range is None:
        log.error("Error: You must specify all of --fsd, --mass and --tank and/or --jump-range.")
        sys.exit(1)
      else:
        self.ship = None

  def run(self):
    with env.use() as envdata:
      start = envdata.parse_station(self.args.start)
      end = envdata.parse_station(self.args.end)

      if start is None:
        log.error("Error: start system/station {0} could not be found. Stopping.".format(self.args.start))
        return
      if end is None:
        log.error("Error: end system/station {0} could not be found. Stopping.".format(self.args.end))
        return

      # Locate all the systems/stations provided and ensure they're valid for our ship
      stations = envdata.parse_stations(self.args.stations)
      for sname in self.args.stations:
        if sname in stations and stations[sname] is not None:
          sobj = stations[sname]
          log.debug("Adding system/station: {0}".format(sobj.to_string()))
          if self.args.pad_size == "L" and sobj.max_pad_size != "L":
            log.warning("Warning: station {0} ({1}) is not usable by the specified ship size.".format(sobj.name, sobj.system_name))
        else:
          log.warning("Error: system/station {0} could not be found.".format(sname))
          return
    stations = list(stations.values())

    # Prefer a static jump range if provided, to allow user to override ship's range
    if self.args.jump_range is not None:
      full_jump_range = self.args.jump_range
      jump_range = self.args.jump_range
    else:
      full_jump_range = self.ship.range()
      jump_range = self.ship.max_range() if self.args.long_jumps else full_jump_range

    calc = c.Calc(ship=self.ship, jump_range=self.args.jump_range, witchspace_time=self.args.witchspace_time, route_strategy=self.args.route_strategy, slf=self.args.slf)
    r = rx.Routing(calc, self.args.rbuffer, self.args.hbuffer, self.args.route_strategy)
    s = solver.Solver(calc, r, jump_range, self.args.diff_limit)

    if self.args.ordered:
      route = [start] + stations + [end]
    else:
      # Add 2 to the jump count for start + end
      route, is_definitive = s.solve(stations, start, end, self.args.num_jumps + 2, self.args.solve_mode)

    if self.args.reverse:
      route = [route[0]] + list(reversed(route[1:-1])) + [route[-1]]

    totaldist = 0.0
    totaldist_sl = 0.0
    totaljumps_min = 0
    totaljumps_max = 0
    totalsc = 0
    totalsc_accurate = True

    output_data = []
    total_fuel_cost = 0.0
    total_fuel_cost_exact = True

    if route is not None and len(route) > 0:
      output_data.append({'src': route[0].to_string()})

      for i in range(1, len(route)):
        cur_data = {'src': route[i-1], 'dst': route[i]}

        if self.args.jump_range is not None:
          full_max_jump = self.args.jump_range - (self.args.jump_decay * (i-1))
          cur_max_jump = full_max_jump
        else:
          full_max_jump = self.ship.range(cargo = self.args.cargo * (i-1))
          cur_max_jump = self.ship.max_range(cargo = self.args.cargo * (i-1)) if self.args.long_jumps else full_max_jump

        cur_data['jumpcount_min'], cur_data['jumpcount_max'] = calc.jump_count_range(route[i-1], route[i], i-1, self.args.long_jumps)
        if self.args.route:
          log.debug("Doing route plot for {0} --> {1}".format(route[i-1].system_name, route[i].system_name))
          if route[i-1].system != route[i].system and cur_data['jumpcount_max'] > 1:
            leg_route = r.plot(route[i-1].system, route[i].system, cur_max_jump, full_max_jump)
          else:
            leg_route = [route[i-1].system, route[i].system]

          if leg_route is not None:
            route_jcount = len(leg_route)-1
            # For hoppy routes, always use stats for the jumps reported (less confusing)
            cur_data['jumpcount_min'] = route_jcount
            cur_data['jumpcount_max'] = route_jcount
          else:
            log.warning("No valid route found for leg: {0} --> {1}".format(route[i-1].system_name, route[i].system_name))
            total_fuel_cost_exact = False
        else:
          total_fuel_cost_exact = False

        cur_data['legsldist'] = route[i-1].distance_to(route[i])
        totaldist_sl += cur_data['legsldist']
        totaljumps_min += cur_data['jumpcount_min']
        totaljumps_max += cur_data['jumpcount_max']
        if route[i].distance is not None and route[i].distance != 0:
          totalsc += route[i].distance
        elif route[i].name is not None:
          # Only say the SC time is inaccurate if it's actually a *station* we don't have the distance for
          totalsc_accurate = False

        cur_fuel = self.ship.tank_size if self.ship is not None else self.args.tank
        if self.args.route and leg_route is not None:
          cur_data['leg_route'] = []
          cur_data['legdist'] = 0.0
          for j in range(1, len(leg_route)):
            ldist = leg_route[j-1].distance_to(leg_route[j])
            cur_data['legdist'] += ldist
            is_long = (ldist > full_max_jump)
            fuel_cost = None
            min_tank = None
            max_tank = None
            if cur_fuel is not None:
              fuel_cost = min(self.ship.cost(ldist, cur_fuel), self.ship.fsd.maxfuel)
              min_tank, max_tank = self.ship.fuel_weight_range(ldist, self.args.cargo * (i-1))
              if max_tank is not None and max_tank >= self.ship.tank_size:
                max_tank = None
              total_fuel_cost += fuel_cost
              cur_fuel -= fuel_cost
              # TODO: Something less arbitrary than this?
              if cur_fuel < 0:
                cur_fuel = self.ship.tank_size if self.ship is not None else self.args.tank
            # Write all data about this jump to the current leg info
            cur_data['leg_route'].append({
                'is_long': is_long, 'ldist': ldist,
                'src': Station.none(leg_route[j-1]), 'dst': Station.none(leg_route[j]),
                'fuel_cost': fuel_cost, 'min_tank': min_tank, 'max_tank': max_tank
            })
          totaldist += cur_data['legdist']

        if route[i].name is not None:
          cur_data['sc_time'] = "{0:.0f}".format(calc.sc_cost(route[i].distance)) if (route[i].distance is not None and route[i].distance != 0) else "???"
        # Add current route to list
        output_data.append(cur_data)

      # Get suitably formatted ETA string
      est_time_min = calc.route_time(route, totaljumps_min)
      est_time_min_m = math.floor(est_time_min / 60)
      est_time_min_s = int(est_time_min) % 60
      est_time_str = "{0:.0f}:{1:02.0f}".format(est_time_min_m, est_time_min_s)
      if totaljumps_min != totaljumps_max:
        est_time_max = calc.route_time(route, totaljumps_max)
        est_time_max_m = math.floor(est_time_max / 60)
        est_time_max_s = int(est_time_max) % 60
        est_time_str += " - {0:.0f}:{1:02.0f}".format(est_time_max_m, est_time_max_s)

      totaljumps_str = "{0:d}".format(totaljumps_max) if totaljumps_min == totaljumps_max else "{0:d} - {1:d}".format(totaljumps_min, totaljumps_max)

      # Work out the max length of the jump distances and jump counts to be printed
      d_max_len = 1
      jmin_max_len = 1
      jmax_max_len = 1
      has_var_jcounts = False
      for i in range(1, len(output_data)):
        od = output_data[i]
        # If we have a hoppy route, we'll only be printing single-jump ranges. If not, we'll be using full leg distances.
        if self.args.format == 'long' and 'leg_route' in od:
          if len(od['leg_route']) > 0:
            d_max_len = max(d_max_len, max([l['ldist'] for l in od['leg_route']]))
        else:
          d_max_len = max(d_max_len, od['legsldist'])
        # If we have estimated jump counts, work out how long the strings will be
        if 'jumpcount_min' in od:
          jmin_max_len = max(jmin_max_len, od['jumpcount_min'])
          jmax_max_len = max(jmax_max_len, od['jumpcount_max'])
          has_var_jcounts = has_var_jcounts or (od['jumpcount_min'] != od['jumpcount_max'])

      # Length = "NNN.nn", so length = len(NNN) + 3 = log10(NNN) + 4
      d_max_len = str(int(math.floor(math.log10(d_max_len))) + 4)
      # Work out max length of jump counts, ensuring >= 1 char
      jmin_max_len = int(math.floor(max(1, math.log10(jmin_max_len)+1)))
      jmax_max_len = int(math.floor(max(1, math.log10(jmax_max_len)+1)))
      # If we have the form "N - M" anywhere, pad appropriately. If not, just use the normal length
      jall_max_len = str(jmin_max_len + jmax_max_len + 3) if has_var_jcounts else str(jmin_max_len)
      jmin_max_len = str(jmin_max_len)
      jmax_max_len = str(jmax_max_len)

      print_summary = True

      if self.args.format in ['long','summary']:
        print("")
        print(route[0].to_string())

        # For each leg (not including start point)
        for i in range(1, len(route)):
          od = output_data[i]
          if self.args.format == 'long' and 'leg_route' in od:
            # For every jump except the last...
            for j in range(0, len(od['leg_route'])-1):
              ld = od['leg_route'][j]
              ld_fuelstr = ''
              if ld['max_tank'] is not None:
                ld_fuelstr = " at {0:.2f}-{1:.2f}T ({2:d}-{3:d}%)".format(
                    ld['min_tank'],
                    ld['max_tank'],
                    int(100.0*ld['min_tank']/self.ship.tank_size),
                    int(100.0*ld['max_tank']/self.ship.tank_size))
              print(("    -{0}- {1: >"+d_max_len+".2f}Ly -{0}-> {2}{3}{4}").format(
                  "!" if ld['is_long'] else "-",
                  ld['ldist'],
                  ld['dst'].to_string(),
                  " [{0:.2f}T]".format(ld['fuel_cost']) if self.ship is not None else '',
                  ld_fuelstr))
            # For the last jump...
            ld = od['leg_route'][-1]
            ld_fuelstr = ''
            if ld['max_tank'] is not None:
              ld_fuelstr = " at {0:.2f}-{1:.2f}T ({2:d}-{3:d}%)".format(
                  ld['min_tank'],
                  ld['max_tank'],
                  int(100.0*ld['min_tank']/self.ship.tank_size),
                  int(100.0*ld['max_tank']/self.ship.tank_size))

            print(("    ={0}= {1: >"+d_max_len+".2f}Ly ={0}=> {2}{5}{6} -- {3:.2f}Ly for {4:.2f}Ly").format(
                "!" if ld['is_long'] else "=",
                ld['ldist'],
                od['dst'].to_string(),
                od['legdist'],
                od['legsldist'],
                " [{0:.2f}T]".format(ld['fuel_cost']) if self.ship is not None else '',
                ld_fuelstr))
          else:
            fuel_fewest = None
            fuel_most = None
            if self.ship is not None:
              # Estimate fuel cost assuming average jump size and full tank.
              fuel_fewest = self.ship.cost(od['legsldist'] / max(0.001, float(od['jumpcount_min']))) * int(od['jumpcount_min'])
              fuel_most = self.ship.cost(od['legsldist'] / max(0.001, float(od['jumpcount_max']))) * int(od['jumpcount_max'])
              total_fuel_cost += max(fuel_fewest, fuel_most)
            # If we don't have "N - M", just print simple result
            if od['jumpcount_min'] == od['jumpcount_max']:
              jumps_str = ("{0:>"+jall_max_len+"d} jump{1}").format(od['jumpcount_max'], "s" if od['jumpcount_max'] != 1 else " ")
            else:
              jumps_str = ("{0:>"+jmin_max_len+"d} - {1:>"+jmax_max_len+"d} jumps").format(od['jumpcount_min'], od['jumpcount_max'])
            route_str = od['dst'].to_string()
            # If the destination is a station, include estimated SC time
            if 'sc_time' in od:
              route_str += ", SC: ~{0}s".format(od['sc_time'])
            fuel_str = ""
            if self.ship is not None:
              if od['jumpcount_min'] == od['jumpcount_max']:
                fuel_str = " [{0:.2f}T{1}]".format(fuel_fewest, '+' if od['jumpcount_min'] > 1 else '')
              else:
                fuel_str = " [{0:.2f}T+ - {1:.2f}T+]".format(min(fuel_fewest, fuel_most), max(fuel_fewest, fuel_most))
            print(("    === {0: >"+d_max_len+".2f}Ly ({1}) ===> {2}{3}").format(od['legsldist'], jumps_str, route_str, fuel_str))

      elif self.args.format == 'short':
        print("")
        sys.stdout.write(str(route[0]))
        for i in range(1, len(route)):
          od = output_data[i]
          if 'leg_route' in od:
            for j in range(0, len(od['leg_route'])):
              ld = od['leg_route'][j]
              sys.stdout.write(", {0}".format(str(ld['dst'])))
          else:
            sys.stdout.write(", {0}".format(str(od['dst'])))
        print("")

      elif self.args.format == 'csv':
        print("{0},{1},{2},{3}".format(
              route[0].system_name,
              route[0].name if route[0].name is not None else '',
              0.0,
              route[0].distance if route[0].uses_sc and route[0].distance is not None else 0))
        for i in range(1, len(route)):
          od = output_data[i]
          if 'leg_route' in od:
            for j in range(0, len(od['leg_route'])-1):
              ld = od['leg_route'][j]
              print("{0},{1},{2},{3}".format(
                    ld['dst'].system_name,
                    ld['dst'].name if ld['dst'].name is not None else '',
                    ld['ldist'],
                    ld['dst'].distance if ld['dst'].uses_sc and ld['dst'].distance is not None else 0))
            ld = od['leg_route'][-1]
            print("{0},{1},{2},{3}".format(
                  od['dst'].system_name,
                  od['dst'].name if od['dst'].name is not None else '',
                  ld['ldist'],
                  od['dst'].distance if od['dst'].uses_sc and od['dst'].distance is not None else 0))
          else:
            print("{0},{1},{2},{3}".format(
                  od['dst'].system_name,
                  od['dst'].name if od['dst'].name is not None else '',
                  od['legsldist'],
                  od['dst'].distance if od['dst'].uses_sc and od['dst'].distance is not None else 0))
        print_summary = False

      if print_summary:
        totaldist_str = "{0:.2f}Ly ({1:.2f}Ly)".format(totaldist, totaldist_sl) if totaldist >= totaldist_sl else "{0:.2f}Ly".format(totaldist_sl)
        fuel_str = "; fuel cost: {0:.2f}T{1}".format(total_fuel_cost, '+' if not total_fuel_cost_exact else '') if total_fuel_cost else ''
        print("")
        print("Total distance: {0}; total jumps: {1}".format(totaldist_str, totaljumps_str))
        print("Total SC distance: {0:d}Ls{1}; ETT: {2}{3}".format(totalsc, "+" if not totalsc_accurate else "", est_time_str, fuel_str))
        print("")

      if self.ship is not None:
        for i in range(1, len(route)):
          od = output_data[i]
          if 'leg_route' in od:
            fcost = 0.0
            for j in range(0, len(od['leg_route'])):
              fcost += self.ship.cost(od['leg_route'][j]['src'].distance_to(od['leg_route'][j]['dst']))
            log.debug("Hop {0} -> {1}, highball fuel cost: {2:.2f}T".format(od['src'].system_name, od['dst'].system_name, fcost))

    else:
      print("")
      print("No viable route found :(")
      print("")


if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
