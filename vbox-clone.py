import xml.etree.ElementTree as ET
import uuid
import sys
import os
import subprocess
import re
import argparse
import shutil

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("machine", help="path to VirtualBox machine file")
arg_parser.add_argument("-n", dest="name", help="applies a new name to the machine")
arg_parser.add_argument("-f", dest="nobackup", help="the backup of original vm file will not be saved", action="store_true")
args = arg_parser.parse_args()

machine_path = args.machine

# check for vm file
if not(os.path.isfile(machine_path)):
    sys.exit("Wrong filename")

# setting path
machine_dir = os.path.dirname(os.path.realpath(machine_path))
os.chdir(machine_dir)

# checking for VBoxManage executable
vbox_shell = ''
for shell in ['vboxmanage', 'VBoxManage']:
    ret = 1
    try:
        with open(os.devnull) as fnull:
            ret = subprocess.call([shell], stdout=fnull, stderr=fnull)
    except:
        pass
    if ret == 0:
        vbox_shell = shell

if vbox_shell == '':
    raise Exception("Can not found VBoxManage executable")


class XMLNSWrapper:
    def __init__(self, path):
        self._path = path
        self._tree = ET.parse(path)
        self._root = self._tree.getroot()

        nm_match_obj = re.match( r'^{(.*)}', self._root.tag)
        if nm_match_obj:
            self._nmspace = nm_match_obj.group(1)
        else:
            self._nmspace = ''

    def get_elements_by_name(self, name = '', ret_first = False):
        elements = []
        for element in self._root.iter('{' + self._nmspace + '}' + name):
            elements.append(element)

        if ret_first:
            return elements[0]
        else:
            return elements

    def get_element_attrs(self, element):
        return element.attrib


    def set_element(self, element, attr, value):
        element.set(attr, value)

    def save_xml(self):
        ET.register_namespace('', self._nmspace)
        self._tree.write(self._path)

class UUIDWrapper:
    @staticmethod
    def generate_uuid():
        return '{' + str(uuid.uuid1()) + '}'

    @staticmethod
    def wrap_uuid(uuid):
        return '{' + uuid + '}'


xml_parser = XMLNSWrapper(machine_path)

machine = xml_parser.get_elements_by_name('Machine', True)

# machine uuid
xml_parser.set_element(machine, 'uuid', UUIDWrapper.generate_uuid())

# machine name
if args.name:
    xml_parser.set_element(machine, 'name', args.name)

# media uuid
uuid_mapping = {};
for hdd in xml_parser.get_elements_by_name('HardDisk'):

    hdd_attrs = xml_parser.get_element_attrs(hdd)
    hdd_uuid = hdd_attrs['uuid']
    hdd_path = hdd_attrs['location']

    vboxmanage_lines = subprocess.check_output([vbox_shell, 'internalcommands', 'sethduuid', hdd_path])
    match_obj = re.match( r'^UUID changed to: (.*)$', vboxmanage_lines)

    new_hdd_uuid = ''
    if match_obj:
        new_hdd_uuid = match_obj.group(1)
    else:
        raise Exception("Wrong hdd uuid")

    uuid_mapping[hdd_uuid] = UUIDWrapper.wrap_uuid(new_hdd_uuid)
    xml_parser.set_element(hdd, 'uuid', UUIDWrapper.wrap_uuid(new_hdd_uuid))

for image in xml_parser.get_elements_by_name('Image'):
        image_uuid = image.get('uuid')
        if image_uuid in uuid_mapping:
            xml_parser.set_element(image, 'uuid', uuid_mapping[image_uuid])

# saving original file
if not args.nobackup:
    shutil.copyfile(machine_path, machine_path + ".orig")

xml_parser.save_xml()
