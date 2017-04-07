import math
import os
import struct
import sys
import util

_vscache_entry_len = 8 # bytes / 64 bits
_vscache_header_len = 6 * _vscache_entry_len
_vscache_eof_marker = 0x5AFEC0DE5AFEC0DE


def parse_visited_stars_cache(filename):
  with open(filename, 'rb') as f:
    # Skip over file header
    f.seek(_vscache_header_len, 0)
    cur_entry = f.read(_vscache_entry_len)
    while cur_entry is not None and len(cur_entry) == _vscache_entry_len:
      # Swap bytes to make it a sensible integer
      cur_id = struct.unpack('<Q', cur_entry)[0]
      # Check if this matches the magic EOF value
      if cur_id == _vscache_eof_marker:
        break
      # Return this ID
      yield cur_id
      cur_entry = f.read(_vscache_entry_len)


def create_import_lists(data):
  count = int(math.ceil(math.log(len(data), 2)))
  lists = [[] for _ in range(count)]
  for idx, s in enumerate(data):
    for i in range(count):
      if (idx & (2**i)) == (2**i):
        lists[i].append(s)
  return lists


def create_import_list_files(data, output_format = 'ImportStars{}.txt'):
  with open(output_format.format('Full'), 'w') as f:
    f.writelines(['{}\n'.format(d) for d in data])
  for i, l in enumerate(create_import_lists(data)):
    with open(output_format.format(i), 'w') as f:
      f.writelines(['{}\n'.format(d) for d in l])


def calculate_id64s_from_lists(names, full, lists):
  if len(names) == 0 or len(full) == 0 or len(lists) == 0:
    return {}
  if len(names) < len(full):
    return {}
  count = 2**len(lists)
  output = {}
  for n in full:
    idx = 0
    for i in range(len(lists)):
      if n in lists[i]:
        idx += (2**i)
    output[names[idx]] = n
  return output

# {18:25:39} ImportStars: unknown star: 'M Centauri'
def calculate_id64s_from_list_files(names_file, full_file, list_files):
  with open(names_file, 'r') as f:
    names = [n.strip() for n in f]
  full = list(parse_visited_stars_cache(full_file))
  lists = []
  for fname in list_files:
    lists.append(list(parse_visited_stars_cache(fname)))
  return calculate_id64s_from_lists(names, full, lists)

