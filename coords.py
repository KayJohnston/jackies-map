#!/usr/bin/env python

from __future__ import print_function
import argparse
import env
import logging

app_name = "coords"

log = logging.getLogger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Display System Coordinates", fromfile_prefix_chars="@", parents=ap_parents, prog = app_name)
    ap.add_argument("system", metavar="system", type=str, nargs="*", help="The system to print the coordinates for")
    self.args = ap.parse_args(arg)

  def run(self):
    maxlen = 0
    with env.use() as envdata:
      systems = envdata.parse_systems(self.args.system)
      for name in self.args.system:
        maxlen = max(maxlen, len(name))
        if name not in systems or systems[name] is None:
          log.error("Could not find system \"{0}\"!".format(name))
          return

    print("")
    for name in self.args.system:
      s = systems[name]
      fmtstr = "  {0:>" + str(maxlen) + "s}: [{1:>8.2f}, {2:>8.2f}, {3:>8.2f}]"
      print(fmtstr.format(name, s.position.x, s.position.y, s.position.z))
    print("")

    return True


if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
  env.stop()
