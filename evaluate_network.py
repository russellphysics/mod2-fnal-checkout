import json
import argparse
import numpy as np
import sys
import time

_default_input_file=None
_default_file_prefix=None

def io_channel_to_tile(ioc):
    tile=int(np.floor((ioc-1-((ioc-1)%4))/4+1))
    return tile



def main(input_file=_default_input_file, \
         file_prefix=_default_file_prefix, \
         **kwargs):
    
    if input_file==None:
        print('Provide network JSON file. Exiting.')
        return
    if file_prefix==None:
        print('Provide output filename string. Exiting.')
        return

    network_dict=dict()
    if input_file!=None:
        with open(input_file,'r') as f: network_dict=json.load(f) 

    iog_tile_cid={}
    mapping=network_dict['network']['miso_us_uart_map']
    for iog in range(1,3,1):
        if str(iog) not in network_dict['network']: continue
        hydra=network_dict['network'][str(iog)]
        for ioc in hydra:
            tile=io_channel_to_tile(int(ioc))
            if (int(iog),tile) not in iog_tile_cid: iog_tile_cid[(int(iog),tile)]=[]
            for node in hydra[ioc]["nodes"]:
                if node['chip_id']!='ext':
                    iog_tile_cid[(int(iog),tile)].append(node['chip_id'])

    total_asic=0
    missing_asics={}
    for key in iog_tile_cid.keys():
        total_asic+=len(iog_tile_cid[key])
        for cid in range(11,111,1):
            if cid not in iog_tile_cid[key]:
                if key not in missing_asics: missing_asics[key]=[]
                missing_asics[key].append(cid)

    stdoutOrigin=sys.stdout
    now=time.strftime("%Y_%m_%d_%H_%M_%Z")
    sys.stdout=open("hydra_completeness_"+now+".txt","w")
    print(total_asic, ' total ASICs configured in hydra networks\n')
    print('ASICs not configured (by chip ID):')
    for key in missing_asics.keys():
        print('IO group ',key[0],\
              ' tile ',key[1],\
              ' chip IDs: ',missing_asics[key])
    sys.stdout.close()
    sys.stdout=stdoutOrigin
    
    return
                


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', default=_default_input_file, \
                        type=str, help='''Network JSON file''')
    parser.add_argument('--file_prefix', default=_default_file_prefix, \
                        type=str, help='''String prepended to file''')
    args = parser.parse_args()
    main(**vars(args))

