from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_scrapli.tasks import send_configs
from nornir_jinja2.plugins.tasks import template_file
from nornir_utils.plugins.tasks.data import load_yaml
import os
from rich import print
import ipdb

nr = InitNornir (config_file="Inventory/config.yaml")

# Clearing the Screen
os.system('clear')

'''
this program will configure VxLAN with Control Plane Address Learning 
(Igress Replication/Head-end Replication) 
This Program will configure/automate only Spine/Leaf switches, vIOS-RTR will be configured as manually
Prerequisite: VAR Files and J2 templates 

CP Learning (Ingress Replication use BGP Unicast for address learning)
CP support to L2 VNI/L3 VNI and IRB 

Variable Files: load variable from VARS(variable files), VARS are define for each host
'''

def config_vxlan_cp_features_j2_template(task):
    cp_Ingress_replication_features_cfg_template = task.run (task=template_file, template=f"vxlan_cp_ingress_replication_features.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_cp_features_cfg'] = cp_Ingress_replication_features_cfg_template.result
    dev_cp_feature_cfg_rendered = task.host['dev_cp_features_cfg']
    dev_vxlan_cp_features_config = dev_cp_feature_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_vxlan_cp_features_config)

def config_vxlan_cp_basic_j2_template (task):
    vxlan_basic_cfg_template = task.run (task=template_file, template=f"vxlan_cp_ingress_replication_basic.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_vxlan_basic_cfg'] = vxlan_basic_cfg_template.result
    dev_vxlan_basic_cfg_rendered = task.host['dev_vxlan_basic_cfg']
    dev_vxlan_basic_config = dev_vxlan_basic_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_vxlan_basic_config)

def config_device_interfaces_j2_template(task):
    int_cfg_template = task.run (task=template_file, template=f"config_dev_int.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_int_cfg'] = int_cfg_template.result
    dev_int_cfg_rendered = task.host['dev_int_cfg']
    dev_int_config = dev_int_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_int_config)
   
def config_iBGP_j2_template(task):
    iBGP_cfg_template = task.run (task=template_file, template=f"bgp.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_bgp_cfg'] = iBGP_cfg_template.result
    dev_bgp_cfg_rendered = task.host['dev_bgp_cfg']
    dev_bgp_config = dev_bgp_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_bgp_config)

def config_tenant_j2_template(task):
    tenant_cfg_template = task.run (task=template_file, template=f"tenant.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_tenant_cfg'] = tenant_cfg_template.result
    dev_tenant_cfg_rendered = task.host['dev_tenant_cfg']
    dev_tenant_config = dev_tenant_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_tenant_config)

def config_evpn_j2_template(task):
    evpn_cfg_template = task.run (task=template_file, template=f"evpn.j2", path=f"J2_Templates/{task.host.platform}")
    task.host['dev_evpn_cfg'] = evpn_cfg_template.result
    dev_evpn_cfg_rendered = task.host['dev_evpn_cfg']
    dev_evpn_config = dev_evpn_cfg_rendered.splitlines()
    task.run (task=send_configs, configs=dev_evpn_config)

def config_VxLAN_Nexus_CP (task):
    # First of all we need to load variables (vars) for hosts using load_yaml, 
    
    # it will return yaml data and store in dictionary form and embend into dic key for each specific device 
    dev_data = task.run (task=load_yaml, file=f"./Hosts_VARS/{task.host.platform}/{task.host}.yaml")
    task.host['dev_vars'] = dev_data.result

    # it will return yaml data and store in dictionary form, 
    # These are commond variables for all devices and used to generate commond configurations for all devices
    common_data = task.run (task=load_yaml, file=f"./Hosts_VARS/{task.host.platform}/common_vars.yaml")
    task.host['common_vars'] = common_data.result
    #Now vars are loaded, Lets configure Devices, in our lab we will configuration 

    # Enabled all required featured for VxLAN CP Ingress replication Deployment
    # We will also enable Jumbo frame because VxLAN packet 
    # is extended with extra headers to avoid fragmentation
    config_vxlan_cp_features_j2_template (task)

    # VxLAN CP Ingress replication Basic Configuration
    config_vxlan_cp_basic_j2_template (task)

    # Interface level configuration (IP add, OSPF, pim etc.using j2 template
    config_device_interfaces_j2_template(task)

    # We will run iBGP on all Spine/Leaf to exchange EVPN Routes
    # iBGP required TCP/IP reachability to neighbors so we  have already configured OSPF as underlay
    # iBGP configuration using j2 template
    config_iBGP_j2_template(task)
    
    # Tenant configuration using j2 template, We will configure tenant only at Leaf
    if task.host['dev_vars']['device_type'] == "leaf":
        config_tenant_j2_template(task)
        """
        Now we need to enable sharing EVPN routes (MAC addresses). This looks a lot like normal BGP configuration.
        In EVPN configuration, each L2VNI needs to have an RD and RT’s assigned. 
        This is because they use a MAC-VRF. 
        In the MP-BGP database, L3 routes and L2 MAC addresses are in separate VRF’s. 
        These values are still set to auto in our case, but are different to the L3VNI’s RD’s and RT’s in MP-BGP.

        I know that this might sound a bit confusing. 
        Just remember that you need to advertise L3 information into BGP, 
        as well as separate L2 information. Even though all this is part of the same tenant,
        L2 and L3 addresses are different, and are treated like they’re different address families. 
        """
        config_evpn_j2_template(task)
    

results = nr.run (task=config_VxLAN_Nexus_CP)
print_result (results)
#ipdb.set_trace()


""""
******************  Verification  ******************
show bgp l2vpn evpn summary
# this command will show ASN of neighbors and state

show nve peers
# this will show us VTEP peers, state and either using CP or DP

show nve vni
# this will show L2/L3 VNIs associated with VTEP interface, it will also shows 
# which multicast group being used for L2VNI, we will see UnicastBGP incase if we using ingress replication for BUM traffic
# it will also shows L2 VLAN associated with L3VNI. 
# L3VNI does not have multicast group because these L3VNIs being used for routing

show vxlan
# this show L2/L3 VLAN to L2/L3 VNI mapping

show l2route evpn mac all
show l2route evpn mac-ip all

show bgp l2vpn evpn
# this show alot of data, details in BGP database
"""