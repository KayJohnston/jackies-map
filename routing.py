import logging
import calc
import env
import math
import sys

log = logging.getLogger("route")

default_rbuffer_ly = 40.0
default_hbuffer_ly = 10.0
hbuffer_relax_increment = 5.0
hbuffer_relax_max = 31.0


class Routing(object):

  def __init__(self, calc, rbuf_base, hbuf_base, route_strategy):
    self._calc = calc
    self._rbuffer_base = rbuf_base
    self._hbuffer_base = hbuf_base
    self._route_strategy = route_strategy
    self._trundle_max_addjumps = 4
    self._trunkle_max_addjumps_mul = 1.0
    self._ocount_initial_boost = 1.0
    self._ocount_relax_inc_mul = 0.01
    self._ocount_reset_dec = 2.0
    self._ocount_reset_full = True
    self._trunkle_leg_size = 5.0
    self._trunkle_search_radius = 10.0
    self._trunkle_search_radius_relax_mul = 0.01

  def lerp(self, in_min, in_max, out_min, out_max, value):
    if in_max == in_min:
      raise Exception("in_min and in_max cannot be the same")
    return out_min + ((out_max - out_min) * (min(in_max, max(0, value - in_min)) / (in_max - in_min)))

  def cylinder(self, stars, vec_from, vec_to, buffer_both):
    denominator = (vec_to - vec_from).length
    candidates = []
    for s in stars:
      numerator = ((s.position - vec_from).cross(s.position - vec_to)).length
      dist = numerator / denominator
      if dist < buffer_both:
        candidates.append(s)

    return candidates

  def circle(self, stars, vec, radius):
    candidates = []
    for s in stars:
      dist = (s.position - vec).length
      if dist < radius:
        candidates.append(s)

    return candidates

  def plot(self, sys_from, sys_to, jump_range, full_range = None):
    if full_range is None:
      full_range = jump_range

    if self._route_strategy == "trundle":
      # My algorithm - slower but pinpoint
      return self.plot_trundle(sys_from, sys_to, jump_range, full_range)
    elif self._route_strategy == "trunkle":
      return self.plot_trunkle(sys_from, sys_to, jump_range, full_range)
    elif self._route_strategy == "astar":
      # A* search - faster but worse fuel efficiency
      return self.plot_astar(sys_from, sys_to, jump_range, full_range)
    else:
      log.error("Tried to use invalid route strategy {0}".format(self._route_strategy))
      return None

  def plot_astar(self, sys_from, sys_to, jump_range, full_range):
    rbuffer_ly = self._rbuffer_base
    with env.use() as envdata:
      stars_tmp = envdata.find_systems_by_aabb(sys_from.position, sys_to.position, rbuffer_ly, rbuffer_ly)
    stars = self.cylinder(stars_tmp, sys_from.position, sys_to.position, rbuffer_ly)
    # Ensure the target system is present, in case it's a "fake" system not in the main list
    if sys_to not in stars:
      stars.append(sys_to)

    valid_neighbour_fn = lambda n, current: n != current and n.distance_to(current) < jump_range
    cost_fn = lambda cur, neighbour, path: self._calc.astar_cost(cur, neighbour, path, full_range)
    return calc.astar(stars, sys_from, sys_to, valid_neighbour_fn, cost_fn)

  def plot_trunkle(self, sys_from, sys_to, jump_range, full_range):
    rbuffer_ly = self._rbuffer_base
    # Get full cylinder to work from
    with env.use() as envdata:
      stars_tmp = envdata.find_systems_by_aabb(sys_from.position, sys_to.position, rbuffer_ly, rbuffer_ly)
    stars = self.cylinder(stars_tmp, sys_from.position, sys_to.position, rbuffer_ly)

    best_jump_count = int(math.ceil(sys_from.distance_to(sys_to) / jump_range))

    sldistance = sys_from.distance_to(sys_to)
    # Current estimate of furthest ahead to look, as the estimated total number of jumps in this leg
    optimistic_count = best_jump_count - self._ocount_initial_boost
    # How many jumps to perform in each leg
    trunc_jcount = self._trunkle_leg_size
    search_radius = self._trunkle_search_radius
    # search_radius = self.lerp(100.0, 200.0, self._trunkle_search_radius_min, self._trunkle_search_radius_max, sys_from.distance_to(sys_to))

    sys_cur = sys_from
    next_centre_star = None
    next_stars = []
    failed_attempts = []
    force_intermediate = False

    log.debug("Attempting to plot from {0} --> {1}".format(sys_from.to_string(), sys_to.to_string()))

    route = [sys_from]
    # While we haven't hit our limit to bomb out...
    while optimistic_count - best_jump_count <= (self._trunkle_max_addjumps_mul * best_jump_count):
      # If this isn't our final leg...
      if next_stars is None or len(next_stars) == 0:
        if force_intermediate or self.best_jump_count(sys_cur, sys_to, jump_range) > trunc_jcount:
          factor = sldistance * (trunc_jcount / optimistic_count)
          # Work out the next position to get a circle of stars from
          next_pos = sys_cur.position + (sys_to.position - sys_cur.position).get_normalised() * factor
          # Get a circle of stars around the estimate
          c_next_stars = self.circle(stars, next_pos, search_radius)
          # Limit them to only ones where it's possible we'll get a valid route
          c_next_stars = [s for s in c_next_stars if self.best_jump_count(sys_cur, s, jump_range) <= trunc_jcount and s not in failed_attempts]
          c_next_stars.sort(key=lambda t: t.distance_to(sys_to))
          # Check we got valid stars
          # If not, bump the count up a bit and start the loop again
          if len(c_next_stars) == 0:
            optimistic_count += self._ocount_relax_inc_mul * best_jump_count
            search_radius += self._trunkle_search_radius_relax_mul * best_jump_count
            continue
          log.debug("Found {0} new stars to check".format(len(c_next_stars)))
          next_stars = c_next_stars
        else:
          next_stars = [sys_to]

      next_star = next_stars[0]

      best_jcount = self.best_jump_count(sys_cur, next_star, jump_range)
      # Only limit to N jumps if we're not on the last leg
      # This prevents getting stuck if we think we can get to sys_to in N, but actually need N+1
      jlimit = max(0, trunc_jcount - best_jcount) if next_star != sys_to else None
      # Use trundle to try and calculate a route
      next_route = self.plot_trundle(sys_cur, next_star, jump_range, full_range, jlimit, starcache = stars_tmp)
      # If our route was invalid or too long, check the next star
      if next_route is None or (next_star != sys_to and len(next_route)-1 > trunc_jcount):
        next_stars = next_stars[1:]
        failed_attempts.append(next_star)
        # If we're out of stars to try from this set, increment the ocount and try again
        if len(next_stars) == 0:
          optimistic_count += self._ocount_relax_inc_mul * best_jump_count
          search_radius += self._trunkle_search_radius_relax_mul * best_jump_count
          log.debug("Attempt failed, bumping oc to {0:.3f}".format(optimistic_count))
        if next_star == sys_to:
          log.debug("Forcing intermediate")
          force_intermediate = True
        continue

      # We have a valid route of the correct length, add it to the main route
      route += next_route[1:]
      sys_cur = next_star
      force_intermediate = False
      search_radius = self._trunkle_search_radius
      next_stars = []
      failed_attempts = [sys_cur]  # This ensures we never test our current location as a potential next_star
      # If we're setting the ocount all the way back to its initial value, do that; otherwise just drop it a bit
      # This ensures that we don't miss any good legs just because the previous leg was a dud
      if self._ocount_reset_full:
        optimistic_count = best_jump_count - self._ocount_initial_boost
      else:
        optimistic_count = math.max(1.0, self._ocount_reset_dec)
      # If we've hit the destination, return with successful route
      if sys_cur == sys_to:
        log.debug("Arrived at {0}".format(sys_to.to_string()))
        return route

      log.debug("Plotted {0} jumps to {1}, continuing".format(len(next_route)-1, next_star.to_string()))

    log.debug("No full-route found")
    return None

  def plot_trundle(self, sys_from, sys_to, jump_range, full_range, addj_limit = None, starcache = None):
    if sys_from == sys_to:
      return [sys_from]

    rbuffer_ly = self._rbuffer_base
    hbuffer_ly = self._hbuffer_base
    if starcache is not None:
      stars_tmp = starcache
    else:
      with env.use() as envdata:
        stars_tmp = envdata.find_systems_by_aabb(sys_from.position, sys_to.position, rbuffer_ly, rbuffer_ly)
    stars = self.cylinder(stars_tmp, sys_from.position, sys_to.position, rbuffer_ly)

    log.debug("{0} --> {1}: systems to search from: {2}".format(sys_from.name, sys_to.name, len(stars)))

    add_jumps = 0
    best_jump_count = self.best_jump_count(sys_from, sys_to, jump_range)

    best = None
    bestcost = None

    while best is None and add_jumps <= self._trundle_max_addjumps and (addj_limit is None or add_jumps <= addj_limit):
      while best is None and (hbuffer_ly < hbuffer_relax_max or hbuffer_ly == self._hbuffer_base):
        log.debug("Attempt %d at hbuffer %.1f, jump count: %d, calculating...", add_jumps, hbuffer_ly, best_jump_count + add_jumps)
        vr = self.trundle_get_viable_routes([sys_from], stars, sys_to, jump_range, add_jumps, hbuffer_ly)
        log.debug("Attempt %d at hbuffer %.1f, jump count: %d, viable routes: %d", add_jumps, hbuffer_ly, best_jump_count + add_jumps, len(vr))
        for route in vr:
          cost = self._calc.trundle_cost(route)
          if bestcost is None or cost < bestcost:
            best = route
            bestcost = cost
        hbuffer_ly += hbuffer_relax_increment
      add_jumps += 1
      hbuffer_ly = self._hbuffer_base

    if best is not None:
      log.debug("Route, length = {0}, cost = {1:.2f}: {2}".format(len(best)-1, bestcost, " --> ".join([str(p) for p in best])))
    else:
      log.debug("No route found")
    return best

  def best_jump_count(self, sys_from, sys_to, jump_range):
    return int(math.ceil(sys_from.distance_to(sys_to) / jump_range))

  def trundle_get_viable_routes(self, route, stars, sys_to, jump_range, add_jumps, hbuffer_ly):
    best_jcount = int(math.ceil(route[0].distance_to(sys_to) / jump_range)) + add_jumps
    vec_mult = 0.5

    return self._trundle_gvr_internal(route, stars, sys_to, jump_range, add_jumps, best_jcount, vec_mult, hbuffer_ly)

  def _trundle_gvr_internal(self, route, stars, sys_to, jump_range, add_jumps, best_jcount, vec_mult, hbuffer_ly):
    cur_dist = route[-1].distance_to(sys_to)
    if cur_dist > jump_range:
      # dir(current_pos --> sys_to) * jump_range
      dir_vec = ((sys_to.position - route[-1].position).get_normalised() * jump_range)
      # Start looking some way down the route, determined by jump count
      start_vec = route[-1].position + (dir_vec * vec_mult)
      end_vec = route[-1].position + dir_vec
      # Get viable stars; if we're adding jumps, use a smaller buffer cylinder to prevent excessive searching
      mystars = self.cylinder(stars, start_vec, end_vec, hbuffer_ly)

      # Get valid next legs
      vsnext = []
      for s in mystars:
        # distance(last_leg, candidate)
        next_dist = route[-1].distance_to(s)
        if next_dist < jump_range:
          dist_jumpN = s.distance_to(sys_to)
          # Is it possible for us to still hit the current total jump count with this jump?
          # jcount = len(route)-1 + the candidate jump = len(route)
          maxd = (best_jcount - len(route)) * jump_range
          if dist_jumpN < maxd:
            vsnext.append(s)

      vrnext = []
      for s in vsnext:
        vrnext = vrnext + self._trundle_gvr_internal(route + [s], stars, sys_to, jump_range, add_jumps, best_jcount, vec_mult, hbuffer_ly)
      return vrnext

    else:
      route.append(sys_to)
      return [route]
