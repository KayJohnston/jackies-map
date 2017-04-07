my_filename = 'tourist_3.csv'
new_filename = 'Tourist Beacons - Beacons 26f 2f.csv'

my_found = []
new_found = []

print('Finding beacons in',my_filename)

with open(my_filename, 'r') as opened:
    readtext = opened.read()
    
lines = readtext.split('\n')

for line in lines:
    try:
        sep = line.split(',')
        my_found.append([int(sep[0]),sep[1]])
    except:
        print('failed on',line)

print('Found',len(my_found),'beacons in',my_filename)
print()

print('Finding beacons in',new_filename)

with open(new_filename, 'r') as opened:
    readtext= opened.read()

lines = readtext.split('\n')
for line in lines:
    try:
        sep = line.split(',')
        new_found.append([int(sep[0]),sep[1]])
    except:
        print('failed on',line)

print('Found',len(new_found),'beacons in',new_filename)
print()

for system in new_found:
    if system[1] != '':
        if system in my_found:
##            print('present')
            alice = 'do nowt'
        else:
            print(system)
