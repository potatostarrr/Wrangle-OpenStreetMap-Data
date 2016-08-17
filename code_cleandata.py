import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import operator
import pprint
#elem is iterator for xml.iterparse, key_value is a default set dictionary,
#update decide whether we want to update our key and value, mapping is the update rule
def create_tag(key_value,update=False):
    for event,elem in ET.iterparse('nashville_tennessee.osm',events =('start',)):
        for tag in elem.iter('tag'):
            if 'k' in tag.attrib and 'v' in tag.attrib:
                key = tag.attrib['k']
                value = tag.attrib['v']
                if not update :
                    key_value[key].add(value)

    return key_value
#tag_keys is a dictionary which represent the number of keys in our dataset
def create_tag_keys(tag_keys):
    for event,elem in ET.iterparse('nashville_tennessee.osm',events =('start',)):
        for tag in elem.iter('tag'):
            if 'k' in tag.attrib:
                key = tag.attrib['k']
                if key in tag_keys:
                    tag_keys[key] +=1
                else:
                    tag_keys[key] = 1
    return tag_keys
#Let take look at our dataset
tag_keys={}
key_value = defaultdict(set)

tag_keys = create_tag_keys(tag_keys)
key_value = create_tag(key_value)

def sort_by_value(dic):
    return sorted(dic.items(), key=operator.itemgetter(1), reverse =True)
sort_tag_keys = sort_by_value(tag_keys)
sort_tag_keys

key_value['building']

key_value['access']

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
street_type = defaultdict(set)
for elem in key_value['addr:street']:
    m = street_type_re.search(elem)
    if m:
        street_type[m.group()].add ( elem)

print(street_type.keys())

mapping = {
'ave' :'Avenue',
'avenue' : 'Avenue',
'Ave' :   'Avenue',
'Blvd' : 'Boulevard',
'Ct': 'Court',
'Crt' : 'Court',
'Dr': 'Drive',
'Ln' :  'Lane',
'pike' : 'Pike',
'Pk' :'Pike',
'pk' : 'Pike',
'Pkwy':'Parkway',
'Pky':'Parkway',
'Rd' : 'Road',
'St':'Street',
'St.':'Street',
'st' :'Street',
'hills':'Hills'
}
#clean street name according to the mapping dictionary
def update_street(name, mapping):
    name_split = name.split(' ')
    if name_split[-1] in mapping:
        name_split[-1] = mapping[name_split[-1]]
        name = " ".join(name_split)

    return name

key_value['addr:state']


def update_state(state):
    if state != "KY":
        state = "TN"
    return state

key_value['addr:city']

#1. we want all the city name start with capital digit.
#2. we just want city name, not in the form of 'city , state', or 'city-courty'
#3. we do not want any quote in name. 'Thompson"s Station',"Thompson's Station",'Thompsons Station' should be transform to
#    'Thompsons Station'
#4. we do not want any mistake in spelling.'Mount Joliet' should be 'Mount Juliet',
#5. There should exist one blank before a capitilized letter
#   'La Vergne',
#    'LaVergne',
#

def update_city(city):
    city = city.split(',')[0]#2
    city = city.split('-')[0]#2
    city = city[0].upper() + city[1:]
    city = city.replace("\"" ,"" )#3
    city = city.replace("'" , "")#3
    if 'Joliet' in city:
        city = city.replace('Joliet','Juliet')#4

    before = None
    index = 0
    for letter in city:
        if not before:
            before = letter
        elif letter.isupper() and before != " ":
            city = city[0:index]+ " "+city[index:]
            index +=1
        else:
            before = letter
        index +=1
    return city

key_value['addr:postcode']
#We want all postcode are 5-digit number
def update_postcode(postcode):
    if not re.match(r'\d{5}$', postcode):
        if postcode=='TN':
            clean_postcode = None
        else:
            clean_postcode = re.findall(r'^(\d{5})-\d{4}$', postcode)
    else:
        clean_postcode = postcode

    return clean_postcode

def update(task,value,mapping):
    if task =='state':
        value = update_state(value)
    elif task == 'city':
        value = update_city(value)
    elif  task == 'street':
        value = update_street(value, mapping)
    elif task == 'postcode':
        value = update_postcode(value)
    return value

import csv
import codecs
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "nashville_tennessee.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

TAG = ['addr:state','addr:city','addr:street','addr:postcode','building','access']

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    if element.tag == 'node':
        for key in NODE_FIELDS:
            node_attribs[key] = element.attrib[key]
    elif element.tag=='way':
        p = 0
        for key in WAY_FIELDS:
            way_attribs[key] = element.attrib[key]
        for nd in element.iter('nd'):
            dic={}
            dic['id'] = element.attrib['id']
            dic['node_id'] = nd.attrib['ref']
            dic['position'] = p
            p += 1
            way_nodes.append(dic)

    for tag in element.iter('tag'):
        tag_type = None
        tag_key = tag.attrib['k']
        m = PROBLEMCHARS.search(tag_key)
        if not m:
            if tag_key in TAG:
                if ':' in tag_key:
                    index = tag_key.find(":")
                    tag_type = tag_key[:index]
                    tag_key = tag_key[index+1:]
                dic = {}
                dic['id'] = element.attrib['id']
                dic['key'] = tag_key
                dic['value'] = update (tag_key ,tag.attrib['v'],mapping)
                if tag_type:
                    dic['type'] = tag_type
                else:
                    dic['type'] = default_tag_type
                tags.append(dic)







    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.iteritems()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=False)





