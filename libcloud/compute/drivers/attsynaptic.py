# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
AT&T Synaptic Cloud (vCloud-1.5 based)
"""


from xml.etree import ElementTree as ET
# from xml.etree.ElementTree import _ElementInterface
# from xml.parsers.expat import ExpatError

from libcloud.compute.drivers.vcloud import VCloud_1_5_NodeDriver
from libcloud.compute.drivers.vcloud import fixxpath


class Compose_1_5_VAppXML(object):
    def __init__(self, name, template, template_vm, network):
        self.name = name
        self.template = template
        self.template_vm = template_vm
        self.network = network
        self._build_xmltree()

    def tostring(self):
        return ET.tostring(self.root)

    def _build_xmltree(self):
        self.root = self._make_instantiation_root()
        # self._add_description("%s" %self.name)
        self._add_instantiation_params(self.root)
        self._add_vapp_template(self.root)
        return

    # def _add_vapp_vm_instantiation_params(self, parent):
        # self._add_network_connection_section(self.root)
        # self._add_guest_customization_section(sparent)

    def _add_guest_customization_section(self, parent):
        guest_custom_section = ET.SubElement(parent, "ns6:GuestCustomizationSection",
            {
                'type' : 'application/vnd.vmware.vcloud.guestCustomizationSection+xml',
                'href' : self.template_vm + '/' + 'guestCustomizationSection/',
                'ns4:required' : "false"
            })
        ET.SubElement(guest_custom_section, "ns4:Info").text = "Specifies Guest OS Customization Settings"
        ET.SubElement(guest_custom_section, "ns6:Enabled").text = "true"
        ET.SubElement(guest_custom_section, "ns6:AdminPasswordEnabled").text = "true"
        ET.SubElement(guest_custom_section, "ns6:AdminPasswordAuto").text = "true"
        ET.SubElement(guest_custom_section, "ns6:ResetPasswordRequired").text = "false"
        ET.SubElement(guest_custom_section, "ns6:ComputerName").text = self.name

        return guest_custom_section

    def _add_network_connection_section(self, parent):
        net_connect_section = ET.SubElement(parent, "ns6:NetworkConnectionSection")
        ET.SubElement(net_connect_section, "ns4:Info")
        network_connection = ET.SubElement(net_connect_section, "ns6:NetworkConnection",
            {'network': self.network.attrib['name']})
        ET.SubElement(network_connection, "ns6:NetworkConnectionIndex").text = "0"
        ET.SubElement(network_connection, "ns6:IsConnected").text = "true"
        ET.SubElement(network_connection, "ns6:IpAddressAllocationMode").text = "POOL"
        return network_connection

    def _add_vapp_template(self, parent):
        sourced_item = ET.SubElement(parent, "ns6:SourcedItem")
        ET.SubElement(sourced_item, "ns6:Source",{
            "name": self.template.name,
            "href": self.template_vm,
            })
        instantionation_params = ET.SubElement(sourced_item, "ns6:InstantiationParams")
        # ET.SubElement(net_connect_section, "ns4:Info")
        self._add_network_connection_section(instantionation_params)
        self._add_guest_customization_section(instantionation_params)
        return sourced_item

    def _add_network_config(self, parent):
        network_config_section = ET.SubElement(parent, "ns6:NetworkConfigSection")
        network_info = ET.SubElement(network_config_section, "ns4:Info")
        net_config = ET.SubElement(network_config_section, "ns6:NetworkConfig", {
            "networkName": self.network.attrib['name']
            })
        config = ET.SubElement(net_config, "ns6:Configuration")
        ET.SubElement(config, "ns6:ParentNetwork",
            {
                "name": self.network.attrib["name"],
                "type": "application/vnd.vmware.vcloud.network+xml",
                "href": self.network.attrib["href"]
            })
        ET.SubElement(config, "ns6:FenceMode").text = "bridged"
        return network_info


    def _add_instantiation_params(self, parent):
        instantionation_params = ET.SubElement(self.root,
                                               "ns6:InstantiationParams")
        self._add_network_config(instantionation_params)


    def _make_instantiation_root(self):
        return ET.Element(
            "ns6:ComposeVAppParams",
            {
            'name': self.name,
            'xml:lang': 'en',
            'xmlns': "http://www.vmware.com/vcloud/v1.5",
            "xmlns:ns2":"http://schemas.dmtf.org/wbem/wscim/1/common",
            "xmlns:ns3":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData",
            "xmlns:ns4":"http://schemas.dmtf.org/ovf/envelope/1",
            "xmlns:ns5":"http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData",
            "xmlns:ns6":"http://www.vmware.com/vcloud/v1.5",
            "xmlns:ns7":"http://www.vmware.com/vcloud/extension/v1.5",
            "xmlns:ns8":"http://schemas.dmtf.org/ovf/environment/1"
            }
        )


class ATT_Synaptic_NodeDriver(VCloud_1_5_NodeDriver):


    def _findvAppTemplateVM(self, image):
        image_info = self.connection.request(image.id).object
        child = image_info.findall(fixxpath(image_info, "Children"))
        vm = child[0].findall(fixxpath(child[0], "Vm"))
        return vm[0].attrib['href']

    def _compose_vapp(self, name, template, template_vm, network):
        compose_vapp = Compose_1_5_VAppXML(name, template, template_vm, network)
        vdc = self.vdcs[0]
        res = self.connection.request(
            "%s/action/composeVApp" %vdc.id,
            data=compose_vapp.tostring(),
            method='POST',
            headers={
                'Content-Type':
                    'application/vnd.vmware.vcloud.composeVAppParams+xml'
            }
        )
        #Fetch the associate Task
        tasks = res.object.findall(fixxpath(res.object, "Tasks"))[0]
        task = tasks.findall(fixxpath(res.object, "Task"))[0]
        if not task.get('href'):
            error = task.findall(fixxpath(task, "Error"))
            raise Exception("Failed to Create Server : Error %s" %error[0].get('message'))

        self._wait_for_task_completion(task.get('href'),timeout=14400)
        vapp_href = res.object.get('href')
        return vapp_href


    def create_node(self, **kwargs):
        """Creates and returns node. If the source image is:
           - vApp template - a new vApp is instantiated from template

        @inherits: L{NodeDriver.create_node}

        @keyword    image:  OS Image to boot on node. (required). Can be a NodeImage or existing Node that will be
                            cloned.
        @type       image:  L{NodeImage} or L{Node}

        @keyword    ex_network: Organisation's network name for attaching vApp VMs to.
        @type       ex_network: C{str}

        @keyword    ex_vdc: Name of organisation's virtual data center where vApp VMs will be deployed.
        @type       ex_vdc: C{str}

        @keyword    ex_vm_names: list of names to be used as a VM and computer name. The name must be max. 15 characters
                                 long and follow the host name requirements.
        @type       ex_vm_names: C{list} of C{str}

        @keyword    ex_vm_cpu: number of virtual CPUs/cores to allocate for each vApp VM.
        @type       ex_vm_cpu: C{int}

        @keyword    ex_vm_memory: amount of memory in MB to allocate for each vApp VM.
        @type       ex_vm_memory: C{int}

        @keyword    ex_deploy: set to False if the node shouldn't be deployed (started) after creation
        @type       ex_deploy: C{bool}
        """

        name = kwargs['name']
        image = kwargs['image']
        ex_vm_names = kwargs.get('ex_vm_names')
        ex_vm_cpu = kwargs.get('ex_vm_cpu')
        ex_vm_memory = kwargs.get('ex_vm_memory')
        ex_deploy = kwargs.get('ex_deploy', True)
        # ex_vdc = kwargs.get('ex_vdc', None)
        # ex_org_network = kwargs.get('ex_org_network', None)
        self._validate_vm_names(ex_vm_names)
        self._validate_vm_cpu(ex_vm_cpu)
        self._validate_vm_memory(ex_vm_memory)


        # vdc = self._get_vdc(ex_vdc)

        #Fetch vAppTemplates Info including associated : VM

        vappTemplateVM = self._findvAppTemplateVM(image)
        networks = self.networks

        vapp_href = self._compose_vapp(name, image, vappTemplateVM, networks[0])

        self.ex_set_vm_cpu(vapp_href, ex_vm_cpu)
        self.ex_set_vm_memory(vapp_href, ex_vm_memory)
        nodes = self.list_nodes()
        vapp = [node for node in nodes if node.name==name][0]
        if ex_deploy:
            self.ex_power_on_node(vapp)

        nodes = self.list_nodes()
        vapp = [node for node in nodes if node.name==name][0]

        return vapp
