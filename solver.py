import logging
import math
import random
import sys
import vector3

log = logging.getLogger("solver")

max_single_solve_size = 12
cluster_size_max = 8
cluster_size_min = 1
cluster_divisor = 10
cluster_iteration_limit = 50
cluster_repeat_limit = 100
cluster_route_search_limit = 4
supercluster_size_max = 8


CLUSTERED         = "clustered"
CLUSTERED_REPEAT  = "clustered-repeat"
BASIC             = "basic"
NEAREST_NEIGHBOUR = "nearest-neighbour"
modes = [CLUSTERED, CLUSTERED_REPEAT, BASIC, NEAREST_NEIGHBOUR]


class _Cluster(object):
  def __init__(self, objs, mean):
    self.position = mean
    self.systems = objs

  @property
  def is_supercluster(self):
    return any(isinstance(s, _Cluster) for s in self.systems)

  def get_closest(self, target):
    best = None
    bestdist = sys.float_info.max
    for s in self.systems:
      if isinstance(s, _Cluster) and s.is_supercluster:
        newsys, newdist = s.get_closest(target)
        if newdist < bestdist:
          best = newsys
          bestdist = newdist
      else:
        newdist = (s.position - target.position).length
        if newdist < bestdist:
          best = s
          bestdist = newdist
    return best, bestdist

  def __repr__(self):
    return "Cluster(size={}, pos={})".format(len(self.systems), self.position)


class Solver(object):
  def __init__(self, calc, route, jump_range, diff_limit):
    self._calc = calc
    self._route = route
    self._diff_limit = diff_limit
    self._jump_range = jump_range


  def solve(self, stations, start, end, maxstops, preferred_mode = CLUSTERED):
    log.debug("Solving set using preferred mode '{}'".format(preferred_mode))
    if preferred_mode == CLUSTERED_REPEAT and len(stations) > max_single_solve_size:
      return self.solve_clustered_repeat(stations, start, end, maxstops), False
    if preferred_mode == CLUSTERED and len(stations) > max_single_solve_size:
      return self.solve_clustered(stations, start, end, maxstops), False
    elif preferred_mode in [CLUSTERED, BASIC]:
      return self.solve_basic(stations, start, end, maxstops), True
    elif preferred_mode == NEAREST_NEIGHBOUR:
      return self.solve_nearest_neighbour(stations, start, end, maxstops), True
    else:
      raise ValueError("invalid preferred_mode flag passed to solve")


  def solve_basic(self, stations, start, end, maxstops):
    result, _ = self.solve_basic_with_cost(stations, start, end, maxstops)
    return result


  def solve_basic_with_cost(self, stations, start, end, maxstops):
    if not any(stations):
      if start == end:
        return [start], 0.0
      else:
        return [start, end], self._calc.solve_cost(start, end, 0)

    log.debug("Calculating viable routes...")
    vr = self._get_viable_routes([start], stations, end, maxstops)
    log.debug("Viable routes: {0}".format(len(vr)))

    count = 0
    costs = []
    mincost = None
    minroute = None

    for route in vr:
      count += 1
      cost_normal = self._calc.solve_route_cost(route)
      route_reversed = [route[0]] + list(reversed(route[1:-1])) + [route[-1]]
      cost_reversed = self._calc.solve_route_cost(route_reversed)

      cost = cost_normal if (cost_normal <= cost_reversed) else cost_reversed
      route = route if (cost_normal <= cost_reversed) else route_reversed

      costs.append(cost)
      if mincost is None or cost < mincost:
        log.debug("New minimum cost: {0} on route {1}".format(cost, count))
        mincost = cost
        minroute = route

    return minroute, mincost


  def solve_nearest_neighbour(self, stations, start, end, maxstops):
    result, _ = self.solve_nearest_neighbour_with_cost(stations, start, end, maxstops)
    return result

  def solve_nearest_neighbour_with_cost(self, stations, start, end, maxstops):
    route = [start]
    full_cost = 0
    remaining = stations
    while any(remaining) and len(route)+1 < maxstops:
      cur_cost = sys.maxsize
      cur_stop = None
      for s in remaining:
        cost = self._calc.solve_cost(route[-1], s, len(route)-1)
        if cost < cur_cost:
          cur_stop = s
          cur_cost = cost
      if cur_stop is not None:
        route.append(cur_stop)
        remaining.remove(cur_stop)
        full_cost += cur_cost
    route.append(end)
    return route, cur_cost


  def solve_clustered(self, stations, start, end, maxstops):
    result, _ = self.solve_clustered_with_cost(stations, start, end, maxstops)
    return result

  def solve_clustered_with_cost(self, stations, start, end, maxstops):
    cluster_count = int(math.ceil(float(len(stations) + 2) / cluster_divisor))
    log.debug("Splitting problem into {0} clusters...".format(cluster_count))
    clusters = find_centers(stations, cluster_count)
    clusters = self._resolve_cluster_sizes(clusters)

    sclusters = self._get_best_supercluster_route(clusters, start, end)

    route = [start]
    cost = 0
    r_maxstops = maxstops - 2

    # Get the closest points in the first/last clusters to the start/end
    _, from_start = self._get_closest_points([start], sclusters[0].systems)
    to_end, _ = self._get_closest_points(sclusters[-1].systems, [end])
    # For each cluster...
    for i in range(0, len(sclusters)-1):
      log.debug("Solving for cluster at index {}...".format(i))
      from_cluster = sclusters[i]
      to_cluster = sclusters[i+1]
      # Get the closest points, disallowing using from_start or to_end
      from_end, to_start = self._get_closest_points(from_cluster.systems, to_cluster.systems, [from_start, to_end])
      # Work out how many of the stops we should be doing in this cluster
      cur_maxstops = min(len(from_cluster.systems), int(round(float(maxstops) * len(from_cluster.systems) / len(stations))))
      r_maxstops -= cur_maxstops
      # Solve and add to the route. DO NOT allow nested clustering, that makes it all go wrong :)
      newroute, newcost = self.solve_basic_with_cost([c for c in from_cluster.systems if c not in [from_start, from_end]], from_start, from_end, cur_maxstops)
      route += newroute
      cost += newcost
      from_start = to_start
    newroute, newcost = self.solve_basic_with_cost([c for c in sclusters[-1].systems if c not in [from_start, to_end]], from_start, to_end, r_maxstops)
    route += newroute
    cost += newcost
    route += [end]
    return route, cost


  def solve_clustered_repeat(self, stations, start, end, maxstops, iterations = cluster_repeat_limit):
    result, _ = self.solve_clustered_repeat_with_cost(stations, start, end, maxstops, iterations)
    return result

  def solve_clustered_repeat_with_cost(self, stations, start, end, maxstops, iterations = cluster_repeat_limit):
    minroute = None
    mincost = sys.float_info.max
    for i in range(0, iterations):
      route, cost = self.solve_clustered_with_cost(stations, start, end, maxstops)
      if cost < mincost:
        mincost = cost
        minroute = route
    return minroute, mincost


  def _resolve_cluster_sizes(self, pclusters):
    clusters = list(pclusters)
    iterations = 0
    while iterations < cluster_iteration_limit:
      iterations += 1
      for i,c in enumerate(clusters):
        if c.is_supercluster:
          c.systems = self._resolve_cluster_sizes(c.systems)
        if len(c.systems) > cluster_size_max:
          log.debug("Splitting oversized cluster {} into two".format(c))
          del clusters[i]
          newclusters = find_centers(c.systems, 2)
          clusters += newclusters
          break
      lengths = [len(c.systems) for c in clusters]
      # If the current state is good, check supercluster size
      if min(lengths) >= cluster_size_min and max(lengths) <= cluster_size_max:
        if len(clusters) <= supercluster_size_max:
          break
        else:
          # Too many clusters, consolidate
          subdiv = int(math.ceil(float(len(clusters)) / supercluster_size_max))
          log.debug("Consolidating from {} to {} superclusters".format(len(clusters), subdiv))
          clusters = find_centers(clusters, subdiv)
          lengths = [len(c.systems) for c in clusters]
          # If everything is now valid...
          if min(lengths) >= cluster_size_min and max(lengths) <= cluster_size_max and len(clusters) <= supercluster_size_max:
              break
    log.debug("Using clusters of sizes {} after {} iterations".format(", ".join([str(len(c.systems)) for c in clusters]), iterations))
    return clusters


  def _get_route_legs(self, stations):
    legs = {}
    for h in stations:
      legs[h] = {}
    for s in stations:
      for t in stations:
        if s.to_string() != t.to_string() and t not in legs[s]:
          log.debug("Calculating leg: {0} -> {1}".format(s.name, t.name))
          leg = self._route.plot(s, t, self._jump_range)
          if leg is None:
            log.warning("Hop route could not be calculated: {0} -> {1}".format(s.name, t.name))
          legs[s][t] = leg
          legs[t][s] = leg

    return legs

  def _get_viable_routes(self, route, stations, end, maxstops):
    # If we have more non-end stops to go...
    if len(route) + 1 < maxstops:
      nexts = {}

      for stn in stations:
        # If this station already appears in the route, do more checks
        if stn in route or stn == end:
          # If stn is in the route at least the number of times it's in the original list, ignore it
          # Add 1 to the count if the start station is *also* the same, since this appears in route but not in stations
          route_matches = len([rs for rs in route if rs == stn])
          stn_matches = len([rs for rs in stations if rs == stn]) + (1 if stn == route[0] else 0)
          if route_matches >= stn_matches:
            continue

        dist = self._calc.solve_cost(route[-1], stn, len(route)-1)
        nexts[stn] = dist

      mindist = min(nexts.values())

      vsnext = []
      for stn, dist in nexts.items():
        if dist < (mindist * self._diff_limit):
          vsnext.append(stn)

      vrnext = []
      for stn in vsnext:
        vrnext = vrnext + self._get_viable_routes(route + [stn], stations, end, maxstops)

      return vrnext

    # We're at the end
    else:
      route.append(end)
      return [route]


  def _get_best_supercluster_route(self, clusters, start, end):
    if len(clusters) == 1:
      return list(clusters)
    first = min(clusters, key=lambda t: t.get_closest(start)[1])
    last = min([c for c in clusters if c != first], key=lambda t: t.get_closest(end)[1])
    log.debug("Calculating supercluster route from {} --> {}".format(first, last))
    log.debug("Clusters: {}".format(clusters))
    if len(clusters) > 3:
      log.debug("Calculating cluster route for {}".format(clusters))
      inter, _ = self._get_best_cluster_route([c for c in clusters if c not in [first, last]], first, last)
    else:
      inter = [c for c in clusters if c not in [first, last]]
    proute = [first] + inter + [last]
    route = []
    for i,c in enumerate(proute):
      if isinstance(c, _Cluster) and c.is_supercluster:
        log.debug("Going deeper... i={}, c={}".format(i, c))
        route += self._get_best_supercluster_route(c.systems, start if i == 0 else route[i-1], end if i >= len(route)-1 else route[i+1])
      else:
        route.append(c)
    return route


  def _get_best_cluster_route(self, clusters, start, end, route = []):
    best = None
    bestcost = sys.float_info.max
    if not route:
      log.debug("In get_best_cluster_route, input = {}, start = {}, end = {}".format(clusters, start, end))
    if len(route) < len(clusters):
      startpt = route[-1].position if any(route) else start.position
      sclusters = sorted([c for c in clusters if c not in route], key=lambda t: (startpt - t.position).length)
      # print("route:", route, "smeans:", smeans)
      for i in range(0, min(len(sclusters), cluster_route_search_limit)):
        c_route, c_cost = self._get_best_cluster_route(clusters, start, end, route + [sclusters[i]])
        if c_cost < bestcost:
          best = c_route
          bestcost = c_cost
    else:
      cur_cost = (start.position - route[0].position).length
      for i in range(1, len(route)):
        cur_cost += (route[i-1].position - route[i].position).length
      cur_cost += (route[-1].position - end.position).length
      best = route
      bestcost = cur_cost
    return (best, bestcost)


  def _get_closest_points(self, cluster1, cluster2, disallowed = []):
    best = None
    bestcost = None
    for n1 in cluster1:
      if n1 in disallowed and len(cluster1) > 1: # If len(cluster) is 1, start == end so allow it
        continue
      for n2 in cluster2:
        if n2 in disallowed and len(cluster2) > 1: # If len(cluster) is 1, start == end so allow it
          continue
        cost = self._calc.solve_cost(n1, n2, 1)
        if best is None or cost < bestcost:
          best = (n1, n2)
          bestcost = cost
    return best


#
# K-means clustering
#
def _cluster_points(X, mu):
  clusters = [[] for i in range(len(mu))]
  for x in X:
    bestmukey = min([(i[0], (x.position - mu[i[0]]).length) for i in enumerate(mu)], key=lambda t: t[1])[0]
    clusters[bestmukey].append(x)
  return clusters


def _reevaluate_centers(mu, clusters):
  newmu = []
  for c in clusters:
    newmu.append(vector3.mean([x.position for x in c]))
  return newmu


def _has_converged(mu, oldmu):
  return (set(mu) == set(oldmu))


def find_centers(X, K):
  # Initialize to K random centers
  oldmu = random.sample([x.position for x in X], K)
  mu = random.sample([x.position for x in X], K)
  clusters = _cluster_points(X, mu)
  while not _has_converged(mu, oldmu):
    oldmu = mu
    # Assign all points in X to clusters
    clusters = _cluster_points(X, mu)
    # Reevaluate centers
    mu = _reevaluate_centers(oldmu, clusters)
  return [_Cluster(clusters[i], mu[i]) for i in range(len(mu))]
