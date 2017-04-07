import logging
from fsd import FSD

log = logging.getLogger("ship")


class Ship(object):
  def __init__(self, fsd_info, mass, tank, cargo = 0):
    # If we already have an FSD object, just use it as-is; otherwise assume a string and create a FSD object
    self.fsd = fsd_info if isinstance(fsd_info, FSD) else FSD(fsd_info)
    self.mass = mass
    self.tank_size = tank
    self.cargo_capacity = cargo

  def max_range(self, cargo = 0):
    return self.fsd.max_range(self.mass, cargo)

  def range(self, fuel = None, cargo = 0):
    return self.fsd.range(self.mass, fuel if fuel is not None else self.tank_size, cargo)

  def cost(self, dist, fuel = None, cargo = 0):
    return self.fsd.cost(dist, self.mass, fuel if fuel is not None else self.tank_size, cargo)

  def max_fuel_weight(self, dist, cargo = 0, allow_invalid = False):
    return self.fsd.max_fuel_weight(dist, self.mass, cargo, allow_invalid)

  def fuel_weight_range(self, dist, cargo = 0, allow_invalid = False):
    return self.fsd.fuel_weight_range(dist, self.mass, cargo, allow_invalid)
