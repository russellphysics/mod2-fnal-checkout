import larpix
from base import utility_base
from base import uart_base
from base import asic_base
import json
import time
#from timebudget import timebudget
#import asyncio


#@timebudget
def network_ext_node(c, io_group, io_channel, iochannel_root_map):
    for ioc in io_channel:
        c.add_network_node(io_group, ioc, c.network_names, 'ext', root=True)
        c.add_network_link(io_group, ioc, 'miso_us', \
                           ('ext', iochannel_root_map[ioc]), 0)
        c.add_network_link(io_group, ioc, 'miso_ds', \
                           (iochannel_root_map[ioc],'ext'), 0)
        c.add_network_link(io_group, ioc, 'mosi', \
                           ('ext', iochannel_root_map[ioc]), 0)
    return



#@timebudget
def network_ext_node_from_tuple(c, iog_ioc_cid):
    c.add_network_node(iog_ioc_cid[0], iog_ioc_cid[1], \
                       c.network_names, 'ext', root=True)
    c.add_network_link(iog_ioc_cid[0], iog_ioc_cid[1], 'miso_us', \
                       ('ext', iog_ioc_cid[2]), 0)
    c.add_network_link(iog_ioc_cid[0], iog_ioc_cid[1], 'miso_ds', \
                       (iog_ioc_cid[2],'ext'), 0)
    c.add_network_link(iog_ioc_cid[0], iog_ioc_cid[1], 'mosi', \
                       ('ext', iog_ioc_cid[2]), 0)
    return


#@timebudget
def configure_chip_id(c, io_group, ioc, chip_id, asic_version):
    setup_key = larpix.key.Key(io_group, ioc, 1)
    if setup_key not in c.chips: c.add_chip(setup_key, version=asic_version)
    c[setup_key].config.chip_id = chip_id
    c.write_configuration(setup_key,'chip_id')
    c.remove_chip(setup_key)
    chip_key=larpix.key.Key(io_group, ioc, chip_id)
    if chip_key not in c.chips: c.add_chip(chip_key, version=asic_version)
    c[chip_key].config.chip_id = chip_id
    return chip_key



#@timebudget
def configure_root_chip(c, chip_key, asic_version, ref_current_trim, \
                        tx_diff, tx_slice, r_term, i_rx):
    if asic_version=='2b':
        c[chip_key].config.ref_current_trim=ref_current_trim
        c.write_configuration(chip_key,'ref_current_trim')
        registers=[]
        for uart in range(4):
            setattr(c[chip_key].config,f'i_rx{uart}', i_rx)
            registers.append(c[chip_key].config.register_map[f'i_rx{uart}'])
            setattr(c[chip_key].config,f'r_term{uart}', r_term)
            registers.append(c[chip_key].config.register_map[f'r_term{uart}'])
        for reg in registers: c.write_configuration(chip_key, reg)
        c[chip_key].config.enable_posi=[0]*4
        c[chip_key].config.enable_posi[1]=1
        c.write_configuration(chip_key, 'enable_posi')
        c[chip_key].config.i_tx_diff0=tx_diff
        c.write_configuration(chip_key, 'i_tx_diff0')
        c[chip_key].config.tx_slices0=tx_slice
        c.write_configuration(chip_key, 'tx_slices0')
        c[chip_key].config.enable_piso_downstream=[0]*4
        c[chip_key].config.enable_piso_downstream[0]=1
        c.write_configuration(chip_key, 'enable_piso_downstream')
        c[chip_key].config.enable_piso_upstream=[0]*4        
        c.write_configuration(chip_key, 'enable_piso_upstream')


        
#@timebudget
def setup_root(c, io, io_group, io_channel, chip_id, verbose, asic_version, \
               ref_current_trim, tx_diff, tx_slice, r_term, i_rx):
#    print('configuring chip id')
    chip_key = configure_chip_id(c, io_group, io_channel, chip_id, asic_version)
#    print('disabling CSA')
    asic_base.disable_chip_csa_trigger(c, chip_key)
#    print('configure root')
    configure_root_chip(c, chip_key, asic_version, ref_current_trim, \
                        tx_diff, tx_slice, r_term, i_rx)
    io.set_reg(0x18, 2**(io_channel-1), io_group=io_group)
#    print('reconcile config')
    ok, diff = utility_base.reconcile_configuration(c, chip_key, verbose)
    if ok:
        if verbose: print(chip_key,' configured')
        io.set_reg(0x18, 0, io_group=io_group)
        return chip_key
    if not ok:
        if verbose: print(chip_key,' NOT configured')
        uart_base.reset_uarts(c, chip_key, verbose)
        ok, diff = utility_base.reconcile_configuration(c, chip_key, \
                                                            verbose)
        c.remove_chip(chip_key)
        io.set_reg(0x18, 0, io_group=io_group)
        return None

async def async_setup_root(c, io, io_group, ioc, chip_id, verbose, \
                           asic_version, ref_current_trim, tx_diff, \
                           tx_slice, r_term, i_rx):
    return await asyncio.to_thread(setup_root, c, io, io_group, ioc, chip_id, verbose, \
                           asic_version, ref_current_trim, tx_diff, \
                           tx_slice, r_term, i_rx)
    

#@timebudget
async def setup_root_async(c, io, io_group, ioc, chip_id, verbose, \
                           asic_version, ref_current_trim, tx_diff, \
                           tx_slice, r_term, i_rx):
    chip_key = configure_chip_id(c, io_group, ioc, chip_id, asic_version)
    asic_base.disable_chip_csa_trigger(c, chip_key)
    configure_root_chip(c, chip_key, asic_version, ref_current_trim, \
                        tx_diff, tx_slice, r_term, i_rx)
    io.set_reg(0x18, 2**(ioc-1), io_group=io_group)
    ok = await utility_base.reconcile_configuration_bool(c, chip_key, verbose)
    #ok, diff = await utility_base.reconcile_configuration(c, chip_key, verbose)
    if ok:
        if verbose: print(chip_key,' configured')
        io.set_reg(0x18, 0, io_group=io_group)
        return await chip_key
    if not ok:
        if verbose: print(chip_key,' NOT configured')
        uart_base.reset_uarts(c, chip_key, verbose)
        ok, diff = utility_base.reconcile_configuration(c, chip_key, \
                                                        verbose)
        #ok, diff = await utility_base.reconcile_configuration_async(c, \
        #                                                            chip_key, \
#                                                                    verbose)
        c.remove_chip(chip_key)
        io.set_reg(0x18, 0, io_group=io_group)
        return await None
    return await None


    
#@timebudget
def setup_root_chips(c, io, io_group, iochannel_root_map, verbose, \
                     asic_version, ref_current_trim, tx_diff, tx_slice, \
                     r_term, i_rx):
    root_keys=[]
    for ioc in iochannel_root_map.keys():
        root_chip_key = setup_root(c, io, io_group, ioc, \
                                   iochannel_root_map[ioc], verbose, \
                                   asic_version, ref_current_trim, \
                                   tx_diff, tx_slice, \
                                   r_term, i_rx)
        if root_chip_key!=None: root_keys.append(root_chip_key)
    return root_keys


#@timebudget
def append_upstream_chip_ids(io_channel, chip_id, waitlist):
    initial=len(waitlist)
    addendum=waitlist
    if io_channel in list(range(1,33,4)):
        for i in range(chip_id,31):
            addendum.add(i); addendum.add(i-10); addendum.add(i+10)
    if io_channel in list(range(2,33,4)):
        for i in range(chip_id,51):
            addendum.add(i); addendum.add(i+10)
    if io_channel in list(range(3,33,4)):
        for i in range(chip_id,81):
            addendum.add(i); addendum.add(i-10)
    if io_channel in list(range(4,33,4)):
        for i in range(chip_id,101):
            addendum.add(i); addendum.add(i-10); addendum.add(i+10)
    return addendum


#@timebudget
def find_daughter_id(parent_piso, parent_chip_id, parent_io_channel):
    if parent_piso==3: daughter_id = parent_chip_id-10
    if parent_piso==1: daughter_id = parent_chip_id+10
    if parent_piso==2: daughter_id = parent_chip_id+1
    if parent_piso==0: daughter_id = parent_chip_id-1
    return daughter_id


#@timebudget
def initial_network(c, io, io_group, root_keys, verbose, asic_version,\
                          ref_current_trim, tx_diff, tx_slice, r_term, i_rx):
    root_ioc=[rk.io_channel for rk in root_keys]
    waitlist=set()
    cnt_configured, cnt_unconfigured=0,0
    firstIteration=True
    for root in root_keys:
        if firstIteration==False:
            print('\n CONFIGURED: ', cnt_configured, \
                  '\t UNCONFIGURED: ',cnt_unconfigured)

        io.set_reg(0x18, 2**(root.io_channel-1), io_group=io_group)
        ok, diff = utility_base.reconcile_configuration(c, root, verbose)
        if ok:
            cnt_configured+=1
        if not ok:
            waitlist=append_upstream_chip_ids(root.io_channel, \
                                              root.chip_id, waitlist)
            cnt_unconfigured=len(waitlist)
            print('Parent ',root,' failed to configure')
            continue
        print(root,'\tconfigured: ',cnt_configured, \
              '\t unconfigured: ',cnt_unconfigured)
        io.set_reg(0x18, 0, io_group=io_group)

        bail=False
        last_chip_id = root.chip_id
        last_daughter=[]
        while last_chip_id<=root.chip_id+9:
            if bail==True: break
            for parent_piso_us in [3,1,2]:
                if bail==True: break                                  
                daughter_id = find_daughter_id(parent_piso_us, last_chip_id, \
                                               root.io_channel)
                # UGLY HACK
                if (last_chip_id, daughter_id) not in last_daughter:
                    last_daughter.append( (last_chip_id, daughter_id) )
                else:
                    bail=True
                if verbose: print('last chip id: ',last_chip_id,\
                                  '\tdaughter chip id: ', daughter_id)

                # UGLY HACK
#                if last_chip_id==60 and daughter_id in [50,70,61]: bail=True
#                if last_chip_id==80 and daughter_id in [70,90,81]: bail=True
                
                # skip known bad I/O ASIC
                if daughter_id==19 and io_group==1 and \
                   root.io_channel in [29,30,31,32]: continue
                if daughter_id<11 or daughter_id>110: continue
                cks=[]
                for ck in c.chips:
                    if ck.io_channel in root_ioc: cks.append(ck.chip_id)
                if daughter_id in cks: continue
                parent=larpix.key.Key(root.io_group, root.io_channel, \
                                      last_chip_id)
                if parent not in c.chips: continue
                daughter=larpix.key.Key(root.io_group, root.io_channel, \
                                        daughter_id)

                ok, diff = uart_base.setup_parent_piso(c, io, parent, \
                                                       daughter, verbose, \
                                                       tx_diff, tx_slice)
                if not ok:
                    print('\t\t==> PARENT PISO US ', parent, \
                          'failed to configure')
                    uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                     verbose, tx_diff, \
                                                     tx_slice)
                    waitlist=append_upstream_chip_ids(root.io_channel, \
                                                      daughter.chip_id, \
                                                      waitlist)
                    cnt_unconfigured=len(waitlist)
                    print(daughter,'\tconfigured: ',cnt_configured,\
                          '\t unconfigured: ',cnt_unconfigured)
                    bail=True
                    continue

                ok, diff, piso = uart_base.setup_daughter(c, io, parent, \
                                                          daughter, verbose, \
                                                          asic_version, \
                                                          ref_current_trim, \
                                                          tx_diff, tx_slice, \
                                                          r_term, i_rx)

                if ok:
                    cnt_configured+=1
                    print(daughter,'\tconfigured: ',cnt_configured,\
                          '\t unconfigured: ',cnt_unconfigured)
                    last_chip_id=daughter.chip_id
                if not ok:
                    print('\t\t==> DAUGHTER ', daughter, \
                          'failed to configure')
                    uart_base.reset_uarts(c, daughter, verbose)
                    uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                     verbose, tx_diff, \
                                                     tx_slice)
                    uart_base.disable_parent_posi(c, parent, daughter, \
                                                  verbose)
                    c.remove_chip(daughter)

                    if parent_piso_us==2:
                        waitlist=append_upstream_chip_ids(root.io_channel, \
                                                      daughter.chip_id, \
                                                      waitlist)
                        bail=True
                    if parent_piso_us!=2:
                        cnt_unconfigured=len(waitlist)
                        print(daughter,'\tconfigured: ',cnt_configured,\
                              '\t unconfigured ',cnt_unconfigured)
                io.set_reg(0x18, 0, io_group=io_group)
            #last_chip_id=daughter.chip_id
        firstIteration=False
    return


#@timebudget
def initial_network_from_root(c, io, io_group, root_key, verbose, asic_version,\
                          ref_current_trim, tx_diff, tx_slice, r_term, i_rx):
    root_ioc=root_key.io_channel
    waitlist=set()
    cnt_configured, cnt_unconfigured=0,0
    io.set_reg(0x18, 2**(root_key.io_channel-1), io_group=io_group)
    ok, diff = utility_base.reconcile_configuration(c, root_key, verbose)
    if ok:
        cnt_configured+=1
    if not ok:
        waitlist=append_upstream_chip_ids(root_key.io_channel, \
                                          root_key.chip_id, waitlist)
        cnt_unconfigured=len(waitlist)
        print('Parent ',root_key,' failed to configure')
        return
    print(root_key,'\tconfigured: ',cnt_configured, \
          '\t unconfigured: ',cnt_unconfigured)
    io.set_reg(0x18, 0, io_group=io_group)

    bail=False
    last_chip_id = root_key.chip_id
    while last_chip_id<=root_key.chip_id+9:
        if bail==True: break
        for parent_piso_us in [3,1,2]:
            if bail==True: break
            daughter_id = find_daughter_id(parent_piso_us, last_chip_id, \
                                           root_key.io_channel)
            cks=[]
            for ck in c.chips:
                if ck.io_channel != root_ioc: cks.append(ck.chip_id)
            if daughter_id in cks: continue
            parent=larpix.key.Key(root_key.io_group, root_key.io_channel, \
                                  last_chip_id)
            daughter=larpix.key.Key(root_key.io_group, root_key.io_channel, \
                                    daughter_id)

            ok, diff = uart_base.setup_parent_piso(c, io, parent, \
                                                   daughter, verbose, \
                                                   tx_diff, tx_slice)
            if not ok:
                print('\t\t==> PARENT PISO US ', parent, \
                      'failed to configure')
                uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                 verbose, tx_diff, \
                                                 tx_slice)
                waitlist=append_upstream_chip_ids(root_key.io_channel, \
                                                  daughter.chip_id, \
                                                  waitlist)
                cnt_unconfigured=len(waitlist)
                print(daughter,'\tconfigured: ',cnt_configured,\
                      '\t unconfigured: ',cnt_unconfigured)
                bail=True
                continue

            ok, diff, piso = uart_base.setup_daughter(c, io, parent, \
                                                      daughter, verbose, \
                                                      asic_version, \
                                                      ref_current_trim, \
                                                      tx_diff, tx_slice, \
                                                      r_term, i_rx)

            if ok:
                cnt_configured+=1
                print(daughter,'\tconfigured: ',cnt_configured,\
                      '\t unconfigured: ',cnt_unconfigured)
            if not ok:
                print('\t\t==> DAUGHTER ', daughter, \
                      'failed to configure')
                uart_base.reset_uarts(c, daughter, verbose)
                uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                 verbose, tx_diff, \
                                                 tx_slice)
                uart_base.disable_parent_posi(c, parent, daughter, \
                                              verbose)
                c.remove_chip(daughter)

                if parent_piso_us==2:
                    waitlist=append_upstream_chip_ids(root_key.io_channel, \
                                                      daughter.chip_id, \
                                                      waitlist)
                    bail=True
                if parent_piso_us!=2:
                    cnt_unconfigured=len(waitlist)
                    print(daughter,'\tconfigured: ',cnt_configured,\
                          '\t unconfigured ',cnt_unconfigured)
            io.set_reg(0x18, 0, io_group=io_group)
            last_chip_id=daughter.chip_id
    return


#@timebudget
def find_waitlist(c, io_group, ioc_range):
    network = {}
    waitlist = []
    for chip_key in c.chips:
        if chip_key.io_group != io_group: continue
        if chip_key.io_channel not in ioc_range: continue
        network[chip_key.chip_id]=chip_key
    for chip_id in range(11,111):
        if chip_id not in network.keys(): waitlist.append(chip_id)
    return waitlist, network


#@timebudget
def find_potential_parents(chip_id, network, verbose):
    parents=[]
    for i in [10,-10,1,-1]:
        if chip_id%10==0 and (chip_id+i)%10==1: continue
        if (chip_id+i)%10==0 and chip_id%10==1: continue
        if chip_id+i in network.keys(): parents.append(network[chip_id+i])
    return parents


#@timebudget
def iterate_waitlist(c, io, io_group, io_channels, verbose, asic_version,\
                     ref_current_trim, tx_diff, tx_slice, r_term, i_rx):
    print('\n\n----- Iterating waitlist ----\n')
    flag=True; outstanding=[]
    while flag==True:
        waitlist, network = find_waitlist(c, io_group, io_channels)
        n_waitlist=len(waitlist)
        oustanding=[]

        for chip_id in waitlist:
            potential_parents=find_potential_parents(chip_id, network, verbose)
            for parent in potential_parents:
                # skip known bad I/O ASIC
                if chip_id==19 and io_group==1 and \
                   parent.io_channel in [29,30,31,32]: continue
                daughter=larpix.key.Key(parent.io_group, parent.io_channel, \
                                        chip_id)

                ok, diff = uart_base.setup_parent_piso(c, io, parent, \
                                                       daughter, verbose, \
                                                       tx_diff, tx_slice)
                if not ok:
                    print('\t\t==> PARENT PISO US ', parent, \
                          'failed to configure')
                    uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                     verbose, tx_diff, tx_slice)
                    io.set_reg(0x18, 0, io_group=io_group)
                    continue

                ok, diff, piso = uart_base.setup_daughter(c, io, parent, \
                                                          daughter, verbose, \
                                                          asic_version, \
                                                          ref_current_trim, \
                                                          tx_diff, tx_slice, \
                                                          r_term, i_rx)
                if ok:
                    waitlist.remove(chip_id)
                    print('WAITLIST RESOLVED\t',daughter)
                    break
                if not ok:
                    print('\t\t==> DAUGHTER ',daughter,' failed to configure')
                    uart_base.reset_uarts(c, daughter, verbose)
                    uart_base.disable_parent_piso_us(c, parent, daughter, \
                                                     verbose, tx_diff, \
                                                     tx_slice)
                    uart_base.disable_parent_posi(c, parent, daughter, \
                                                  verbose)
                    c.remove_chip(daughter)
                    outstanding.append((daughter, piso))
                io.set_reg(0x18, 0, io_group=io_group)

        if n_waitlist==len(waitlist):
            print('\n',len(waitlist),' NON-CONFIGURED chips\n',waitlist,'\n')
            flag=False
        else:
            print('\n\n*****RE-TESTING ',len(waitlist),' CHIPS\n',waitlist)
    return outstanding


#@timebudget
def configure_asic_network_links(c):
    for chip_key in c.chips:
        piso_us = c[chip_key].config.enable_piso_upstream
        for uart in range(len(piso_us)):
            if piso_us[uart]!=1: continue
            if uart==3: daughter_chip_id = chip_key.chip_id-10
            if uart==1: daughter_chip_id = chip_key.chip_id+10
            if uart==2: daughter_chip_id = chip_key.chip_id+1
            if uart==0: daughter_chip_id = chip_key.chip_id-1
            c.add_network_link(chip_key.io_group, chip_key.io_channel, \
                               'miso_us', \
                               (chip_key.chip_id, daughter_chip_id), uart)
        piso_ds = c[chip_key].config.enable_piso_downstream
        for uart in range(len(piso_ds)):
            if piso_ds[uart]!=1: continue
            if uart==3: daughter_chip_id = chip_key.chip_id-10
            if uart==1: daughter_chip_id = chip_key.chip_id+10
            if uart==2: daughter_chip_id = chip_key.chip_id+1
            if uart==0: daughter_chip_id = chip_key.chip_id-1
            c.add_network_link(chip_key.io_group, chip_key.io_channel, \
                               'miso_ds', \
                               (chip_key.chip_id, daughter_chip_id), uart)
        posi = c[chip_key].config.enable_posi
        for uart in range(len(posi)):
            if posi[uart]!=1: continue
            if uart==0: mother_chip_id = chip_key.chip_id-10
            if uart==2: mother_chip_id = chip_key.chip_id+10
            if uart==3: mother_chip_id = chip_key.chip_id+1
            if uart==1: mother_chip_id = chip_key.chip_id-1
            c.add_network_link(chip_key.io_group, chip_key.io_channel, \
                               'mosi', \
                               (chip_key.chip_id, mother_chip_id), uart)
    return c


#@timebudget
def miso_us_chip_id_list(chip2chip_pair, miso_us):
    if chip2chip_pair[0]=='ext' or chip2chip_pair[1]=='ext':
        miso_us[3]=chip2chip_pair[1]
        return miso_us
    if chip2chip_pair[1]-chip2chip_pair[0]==1:
        miso_us[3]=chip2chip_pair[1] # piso 2                                  
    if chip2chip_pair[1]-chip2chip_pair[0]==-1:
        miso_us[1]=chip2chip_pair[1] # piso 0
    if chip2chip_pair[1]-chip2chip_pair[0]==-10:
        miso_us[0]=chip2chip_pair[1] # piso 3                                  
    if chip2chip_pair[1]-chip2chip_pair[0]==10:
        miso_us[2]=chip2chip_pair[1] # piso 1                                  
    return miso_us


def write_network_to_file(c, file_prefix, io_group_pacman_tile, unconfigured, \
                          layout="2.5.1"):

    d=dict()
    d["_config_type"]="controller"
    d["name"]=file_prefix
    d["asic_version"]="2b"
    d["layout"]=layout

    c = configure_asic_network_links(c)
    d["network"]={}
    for iog in io_group_pacman_tile.keys():
        d["network"][iog]={}
        io_channels=utility_base.tile_to_io_channel(io_group_pacman_tile[iog])
        for ioc in io_channels:
            d["network"][iog][ioc]={}
            d["network"][iog][ioc]["nodes"]=[]
            for node in list(c.network[iog][ioc]['miso_us']):
                temp={}
                temp["chip_id"]=node
                miso_us=[None]*4
                for edge in list(c.network[iog][ioc]['miso_us'].edges()):
                    for chip2chip_pair in \
                        c.network[iog][ioc]['miso_us'].edges(edge):
                        if chip2chip_pair[0]==node:
                            miso_us_chip_id_list(chip2chip_pair, miso_us)
                temp["miso_us"]=miso_us
                if c.network[iog][ioc]['miso_us'].nodes[node]['root']==True:
                    temp["root"]=True
                d["network"][iog][ioc]["nodes"].append(temp)
    d["network"]["miso_us_uart_map"]=[3,0,1,2]
    d["network"]["miso_ds_uart_map"]=[1,2,3,0]
    d["network"]["mosi_uart_map"]=[2,3,0,1]

    d["missing"]={}
    for pair in unconfigured:
        key = pair[0]
        if key.io_group not in d["missing"]:
            d["missing"][key.io_group]={}
        if key.io_channel not in d["missing"][key.io_group]:
            d["missing"][key.io_group][key.io_channel]={}
        if key.chip_id not in d["missing"][key.io_group][key.io_channel]:
            d["missing"][key.io_group][key.io_channel][key.chip_id]=[]
        d["missing"][key.io_group][key.io_channel][key.chip_id].append(pair[1])

    now=time.strftime("%Y_%m_%d_%H_%M_%Z")
    if file_prefix!=None: fname=file_prefix+'-network-'+now+'.json'
    if file_prefix==None: fname='network-'+now+'.json'
    with open(fname,'w') as out:
        json.dump(d, out, indent=4)
    print('network JSON: ',fname)

    return fname
