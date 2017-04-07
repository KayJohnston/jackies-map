# Read .json file testbed
# Crude, but working.

import re

class SS():
    def __init__(self,name,x,y,z):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.distance = ((x ** 2) + (y ** 2) + (z ** 2)) ** 0.5
        self.my_x = x
        self.my_y = z
        self.my_z = y

def parseline(line):
    alpha = line.split('\":\"')
    beta = alpha[1].split('\",\"')
    name = beta[0]
    gamma = beta[1].split(',')
    
    x_str = gamma[0].split('\"x\":')
    x = float(x_str[1])
    
    y_str = gamma[1].split('\"y\":')
    y = float(y_str[1])
    
    z_gam = gamma[2].split('}')
    z_str = z_gam[0].split('\"z\":')
    z = float(z_str[1])
    
    new_SS = SS(name,x,y,z)
    return new_SS

filename = 'systemsWithCoordinates2.json'

print('Opening file',filename)

with open(filename, 'r') as opened:
    readtext = opened.read()

print('Opened.')

print()
print('Splitting into lines.')

lines = readtext.split('\n')
readtext = '' # To keep memory use reasonable!

print('Split.')

##target = 'NGC '
##targets = []
##
##print()
##print('Searching for target',target)
##
##counter = 0
##
##for line in lines:
##    if target in line:
##        counter += 1
##        try:
##            targets.append(parseline(line))
##        except:
##            print('failed')
##
##print('Finished search, found',counter,'examples.')
##
### Find unique e.g. NGC whatever.
##uniques = []
##
##for target in targets:
##    if 'Sector' not in target.name:
##        name = target.name.split(' ')
##        result = name[1]
##        if result not in uniques:
##            uniques.append(result)
##            print(target.name)
##
##uniques.sort()

##with open('uniques.csv','w') as opened:
##    for u in uniques:
##        opened.write(u)
##        opened.write('\n')

print()
print('Searching for non-sector, non-region.')

indiv = []

counter = 0

# Precompile the seach string ("if it starts with a space, then has two character, a dash, another character and a space")
# To save a little time when performing this search repeatedly.
scomp = re.compile('(?<= )..-. ')

for line in lines:
    try:
        candidate = parseline(line)
        cn = candidate.name
##        # Might not need this step, now.
##        if 'Dark Region' not in cn and 'Sector' not in cn:
        # Discount proc-gen sector names.  Hopefully this doesn't kill other names.
        matches = re.search(scomp,cn)
        if not matches:
            indiv.append(candidate)
            counter += 1
    except:
        print('Failed on',line)

print('Finished search, found',counter,'not in sectors and dark regions.')

filename = 'findiv.csv'

with open(filename,'w') as opened:
    for star in indiv:
        opened.write(star.name + ',')
        opened.write(str(star.my_x) + ',')
        opened.write(str(star.my_y) + ',')
        opened.write(str(star.my_z) + ',')
        opened.write(str(star.distance) + '\n')
