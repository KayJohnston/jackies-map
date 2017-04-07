import logging
import pgdata
import pgnames
import sector
import json
import math
import sys
import time
import env
from pgnames import log

def run_test(it):
  teststart = time.clock()

  alls = 0
  ok1 = 0
  ok2 = 0
  okha = 0
  okhaname = 0
  bad1 = 0
  bad2 = 0
  badha = 0
  badhaname = 0
  none1 = 0
  none2 = 0
  noneha = 0
  notpg = 0

  for system in it:
    alls += 1
    sysname = pgnames.get_canonical_name(system.name)
    if sysname is not None:
      m = pgdata.pg_system_regex.match(sysname)
      if m is not None:
        if m.group("sector").lower() in pgdata.ha_sectors:
          sect = pgdata.ha_sectors[m.group("sector").lower()]
          is_noneha = False
          if sect.contains(system.position):
            rp, rpe = pgnames._get_relpos_from_sysid(*m.group("l1", "l2", "l3", "mcode", "n1", "n2"))
            if rp is None or rpe is None:
              log.info("BadRelPos: could not calculate relative position for {}".format(system.name))
              badha += 1
              continue
            elif any([s > (sector.sector_size + rpe) for s in rp]):
              log.info("BadRelPos: invalid relpos for {}".format(system.name))
              badha += 1
              continue
            so = sect.get_origin(rpe * 2)
            coords = so + rp
            dx = abs(coords.x - system.position.x)
            dy = abs(coords.y - system.position.y)
            dz = abs(coords.z - system.position.z)
            realdist = (coords - system.position).length
            if dx <= rpe and dy <= rpe and dz <= rpe:
              okha += 1
            else:
              badha += 1
              absdiff = abs(coords - system.position)
              log.info("BadHA{5}: {4}, {0} not close enough to {1} with {2:.0f}Ly/axis uncertainty, actually {3}".format(coords, system.position, rpe, absdiff, system.name, " (minor)" if absdiff.x < (dist+1) and absdiff.y < (dist+1) and absdiff.z < (dist+1) else ""))
          else:
            noneha += 1
            is_noneha = True
            log.info("NoneHA: {0} @ {1} not in {2}".format(system.name, system.position, sect))
          if not is_noneha:
            ha_name = pgnames._ha_get_name(system.position)
            if ha_name == m.group("sector"):
              okhaname += 1
            else:
              badhaname += 1
              if ha_name is not None:
                log.info("BadHAName: {} ({}Ly) was predicted to be in {} ({}Ly)".format(system.name, sect.size, ha_name, pgdata.ha_sectors[ha_name.lower()].size))
              else:
                log.info("BadHAName: {} ({}Ly) was predicted to not be in an HA sector".format(system.name, sect.size))
        else:
          start = time.clock()
          sect = pgnames.get_sector(m.group("sector"))
          tm = time.clock() - start
          if sect is not None:
            cls = sect.sector_class
            pos_sect = pgnames.get_sector(system.position, allow_ha=False)
            if sect == pos_sect:
              start = time.clock()
              coords, dist = pgnames._get_coords_from_name(system.name)
              tm = time.clock() - start
              if coords is None or dist is None:
                log.warning("BadName: could not get coords for {0}".format(system.name))
                if cls == 'c2':
                  bad2 += 1
                elif cls == 'c1':
                  bad1 += 1
                continue
              dx = abs(coords.x - system.position.x)
              dy = abs(coords.y - system.position.y)
              dz = abs(coords.z - system.position.z)
              realdist = (coords - system.position).length
              if dx <= dist and dy <= dist and dz <= dist:
                if cls == 'c2':
                  ok2 += 1
                elif cls == 'c1':
                  ok1 += 1
              else:
                if cls == 'c2':
                  bad2 += 1
                elif cls == 'c1':
                  bad1 += 1
                absdiff = abs(coords - system.position)
                log.info("Bad position{5}: {4}, {0} not close enough to {1} with {2:.0f}Ly/axis uncertainty, actually {3}".format(coords, system.position, dist, absdiff, system.name, " (minor)" if absdiff.x < (dist+1) and absdiff.y < (dist+1) and absdiff.z < (dist+1) else ""))
            else:
              if cls == 'c2':
                bad2 += 1
              elif cls == 'c1':
                bad1 += 1
              log.info("Bad sector: {0} @ {1} is not in {2}".format(system.name, system.position, sect))
          else:
            if cls == 'c2':
              none2 += 1
              log.info("None2: {0} @ {1}".format(system.name, system.position))
            elif cls == 'c1':
              none1 += 1
              log.info("None1: {0} @ {1}".format(system.name, system.position))
            else:
              log.info("InvalidName: {0} @ {1}".format(system.name, system.position))
      else:
        notpg += 1
    else:
      notpg += 1
  
  duration = time.clock() - teststart

  log.info("Totals: All = {}, OK1 = {}, OK2 = {}, OKHA = {}, OKHAName = {}, Bad1 = {}, Bad2 = {}, BadHA = {}, BadHAName = {}, None1 = {}, None2 = {}, NoneHA = {}, notPG = {}".format(alls, ok1, ok2, okha, okhaname, bad1, bad2, badha, badhaname, none1, none2, noneha, notpg))
  log.info("Time: {0:.6f}s, {1:.6f}s per system".format(duration, duration / alls))



# Test modes
if __name__ == '__main__':
  if len(sys.argv) >= 2:
    if sys.argv[1] == "c1ot":
      test_data = {
        'Mycapp': 623548, 'Lychoitl': 541608, 'Shruery': 410512, 'Phrauph': 574396,
        'Myreasp': 459657, 'Pythaics': 557994, 'Pythaipr': 803991, 'Styaill': 214060,
        'Styefs': 836644, 'Leeh': 99373, 'Keet': 99364, 'Schreang': 607155,
        'Sqeass': 263332, 'Squer': 639916, 'Cryaths': 246810, 'Phylur': 328741,
        'Slyeax': 443539, 'Mynoaw': 541610, 'Gyruenz': 459554, 'Sphuezz': 132132,
        'Spliech': 132135, 'Groec': 164896, 'Vigs': 148514, 'Tzorbs': 115616,
        'Phloiws': 115617, 'Tyrootz': 164768, 'Sigy': 148381, 'Soac': 148389,
        'Pyoer': 492698,
        # 'Isheau': 99239, 'Aowheou': 574476, 'Aochou': 492476,
        # 'Aaeyoe': 623543, 'Aaeshoa': 705543, 'Eaezi': 820396, 
        # Nasty ones
        'Chroabs': 492710, 'Kyloalz': 574382, 'Flyaulz': 574516, 'Froaphs': 492589,
        'Swoiphs': 312233, 'Cyoilz': 213923,
      }
      badcnt = 0
      for name in dict(test_data):
        actual = test_data[name]
        predicted = pgnames._c1_get_offset(name)
        if actual != predicted:
          print("BAD [{0}]: predicted = {1}, actual = {2}, diff = {3}".format(name, predicted, actual, round(abs(predicted-actual)/pgdata.cx_prefix_total_run_length)))
          badcnt += 1
      print("Total: OK = {0}, bad = {1}".format(len(test_data)-badcnt, badcnt))

    elif sys.argv[1] == "run2":
      input = sys.argv[2] # "Schuae Flye"
      limit = int(sys.argv[3]) if len(sys.argv) > 3 else None

      for idx, frags in pgnames._c2_get_run(input, limit):
        x = sector.base_coords.x + (idx * sector.sector_size)
        print ("[{1}/{2}] {0}".format(pgnames.format_name(frags), idx, x))
      
    elif sys.argv[1] == "fr2":
      limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1248
      
      x = -sector.base_sector_index[0]
      y = -8
      z = -sector.base_sector_index[2]
      count = 0
      ok = 0
      bad = 0
      for ((f0, f1), (f2, f3)) in pgnames._c2_get_start_points():
        extra = ""
        if y >= -3 and y <= 2:
          sect = pgnames._c2_get_name(sector.PGSector(x,y,z))
          if sect == [f0, f1, f2, f3]:
            ok += 1
            # print("[{0},{1},{2}] {3}{4} {5}{6} (OK: {7})".format(x,y,z,f0,f1,f2,f3,pgnames.format_name(sect)))
          elif sect is not None:
            bad += 1
            print("[{0},{1},{2}] {3}{4} {5}{6} (BAD: {7})".format(x,y,z,f0,f1,f2,f3,pgnames.format_name(sect)))
          else:
            # print("[{0},{1},{2}] {3}{4} {5}{6}".format(x,y,z,f0,f1,f2,f3))
            pass
        else:
          # print("[{0},{1},{2}] {3}{4} {5}{6}".format(x,y,z,f0,f1,f2,f3))
          pass
        y += 1
        if y >= 8:
          y = -8
          z += 1
        if count + 1 > limit:
          break
        count += 1
      print("Count: {0}, OK: {1}, bad: {2}".format(count, ok, bad))

    elif sys.argv[1] == "search2":
      input = sys.argv[2]
      syst = pgnames.get_system(input)
      if syst is not None:
        coords, relpos_confidence = syst.position, syst.uncertainty
        print("Est. position of {0}: {1} (+/- {2}Ly)".format(input, coords, int(relpos_confidence)))
      else:
        sect = pgnames.get_sector(input)
        if sect is not None:
          print("{0} is {1}, has origin {2}".format(input, str(sect), sect.origin))
        else:
          print("Could not find sector or system")

    elif sys.argv[1] == "eddbtest":
      env.set_verbosity(2)
      
      with env.use() as envdata:
        run_test(envdata.find_all_systems())

    elif sys.argv[1] == "nametest":
      env.set_verbosity(2)

      ok = 0
      bad = 0

      with env.use() as envdata:
        for s in envdata.find_all_systems():
          m = pgdata.pg_system_regex.match(s.name)
          if m is not None:
            cls = pgnames._get_sector_class(m.group("sector"))
            if cls is not None:
              predsys = pgnames.get_system(s.position, m.group("mcode"))
              if s.name.lower().startswith(predsys.name.lower()):
                ok += 1
              else:
                log.info("Bad: {} @ {} should be {}?".format(s.name, s.position, predsys.name))
                bad += 1

      log.info("Checked {} systems, OK: {}, bad: {}".format(ok + bad, ok, bad))

    elif sys.argv[1] == "sectortest":
      env.set_verbosity(2)

      ok = 0
      bad = 0

      with env.use() as envdata:
        sectors = {}
        for s in envdata.find_all_systems():
          m = pgdata.pg_system_regex.match(s.name)
          if m is not None:
            if m.group("sector") not in sectors:
              sectors[m.group("sector")] = 0
            sectors[m.group("sector")] += 1

      for s in [k for (k, v) in sectors.items() if v > 0]:
        cls = pgnames._get_sector_class(s)
        if cls in [1,2]:
          log.debug("Checking {}".format(s))
          sec = pgnames.get_sector_from_name(s)
          if sec is None:
            continue
          c1name = pgnames._c1_get_name(sec.centre)
          c1off = pgnames._c1_get_offset(c1name)
          pcls = pgnames._get_c1_or_c2(c1off)
          if cls != pcls:
            bad += 1
            log.info("Wrong class: actual {} ({}, class {}), predicted class {}".format(s, c1off, cls, pcls))
          else:
            ok += 1

      log.info("Checked {} sectors, OK: {}, bad: {}".format(len(sectors), ok, bad))

    elif sys.argv[1] == "eddbspaff":
      with open("edsm_data.txt") as f:
        edsm_sectors = [s.strip() for s in f.readlines() if len(s) > 1]

      y_levels = {}
     
      with env.use() as envdata: 
        for system in envdata.find_all_systems():
          m = pgdata.pg_system_regex.match(system.name)
          if m is not None and m.group("sector") in edsm_sectors:
            sname = m.group("sector")
            cls = pgnames._get_sector_class(m.group("sector"))
            if cls != "2":
              sect = pgnames.get_sector(system.position, allow_ha=False)
              if sect.y not in y_levels:
                y_levels[sect.y] = {}
              if sect.z not in y_levels[sect.y]:
                y_levels[sect.y][sect.z] = {}
              if sect.x not in y_levels[sect.y][sect.z]:
                y_levels[sect.y][sect.z][sect.x] = {}
              if sname not in y_levels[sect.y][sect.z][sect.x]:
                y_levels[sect.y][sect.z][sect.x][sname] = 0
              y_levels[sect.y][sect.z][sect.x][sname] += 1

      xcount = sector.galaxy_size[0]
      zcount = sector.galaxy_size[2]
      for y in y_levels:
        with open("sectors_{0}.csv".format(y), 'w') as f:
          for z in range(zcount - sector.base_sector_index[2], -sector.base_sector_index[2], -1):
            zvalues = ["" for _ in range(xcount)]
            if z in y_levels[y]:
              for x in range(-sector.base_sector_index[0], xcount - sector.base_sector_index[0], 1):
                if x in y_levels[y][z]:
                  zvalues[x + sector.base_sector_index[0]] = max(y_levels[y][z][x], key=lambda t: y_levels[y][z][x][t])
            f.write(",".join(zvalues) + "\n")
    else:
      print("Unknown test {0}".format(sys.argv[1]))
  else:
    print("Usage: {0} <test-name> [<test-args>]".format(sys.argv[0]))
