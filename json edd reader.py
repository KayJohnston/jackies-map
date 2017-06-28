# json-edd.json to .csv file converter

class landmark():

    def __init__(self,number,l_type,name,system,x,y,z,desc):
        self.number = number
        self.l_type = l_type
        self.name = name
        self.system = system
        self.x = x
        self.y = y
        self.z = z
        self.desc = desc

    def report(self):
        print('id:',self.number,'type:',self.l_type,'name:',self.name)
        print('system:',self.system,'x:',self.x,'y:',self.y,'z:',self.z)
        print('desc:',self.desc)

def make_landmark_from_chunk(text):
    number = search_json_chunk(text,'id')
    l_type = search_json_chunk(text,'type')
    name = search_json_chunk(text,'name')
    system = search_json_chunk(text,'galMapSearch')
    x,z,y = search_json_chunk_for_coords(text)
    desc = search_json_chunk(text,'descriptionMardown')
    new_landmark = landmark(number,l_type,name,system,x,y,z,desc)
    return new_landmark

def search_json_chunk(text,target):
    b1 = '\"' + target + '\":'
    broken = text.split(b1)
##    print(b1)
##    print(broken)
    b2 = broken[1].split('\"')
##    print(b2)
    b3 = b2[1]
##    print(target,b3)
    return b3

def search_json_chunk_for_coords(text):
    b1 = '\"coordinates\":['
    broken = text.split(b1)
##    print(broken)
    b2 = broken[1].split(']')
    b3 = b2[0]
    b4 = b3.split(',')
    return b4[0],b4[1],b4[2]

filename = 'json-edd.json'

with open(filename, 'r') as opened:
    readtext = opened.read()

lines = readtext.split('},{')

print('Found',len(lines),'lines in the file.')

landmarks = []

failcount = 0
for line in lines:
    try:
        new_landmark = make_landmark_from_chunk(line)
        landmarks.append(new_landmark)
    except:
        failcount += 1
        # Fails on regions and routes at the moment.

print('Failed on',failcount,'lines.')

filename = 'json edd landmarks.csv'

with open(filename, 'w') as opened:
    for l in landmarks:
        opened.write(l.number)
        opened.write(',')
        opened.write(l.l_type)
        opened.write(',')
        opened.write(l.name)
        opened.write(',')
        opened.write(l.system)
        opened.write(',')
        opened.write(str(l.x))
        opened.write(',')
        opened.write(str(l.y))
        opened.write(',')
        opened.write(str(l.z))
        opened.write(',')
        d = l.desc.replace(',','')
        opened.write(d)
        opened.write('\n')
