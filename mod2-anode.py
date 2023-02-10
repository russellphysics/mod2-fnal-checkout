# *****************************************************
# Input file assumed to have the following structure:
# JSON dict
# key = chip-key string
# value = list of lists of [[mean,std]] for 64 channels
# *******************************************************

import matplotlib.pyplot as plt
import yaml
import numpy as np
import argparse
import json
from copy import copy
from matplotlib.patches import Rectangle
from matplotlib import cm
from matplotlib.colors import Normalize

pitch=3.8 # mm

_default_geometry_path=None
_default_input_json=None
_default_file_prefix=None
_default_metric=None
_default_normalization=50.

def load_yaml(geometry_path):
    with open(geometry_path) as fi:
        geo = yaml.full_load(fi)
        chip_pix = dict([(chip_id, pix) for chip_id,pix in geo['chips']])
        vlines=np.linspace(-1*(geo['width']/2), geo['width']/2, 11)
        hlines=np.linspace(-1*(geo['height']/2), geo['height']/2, 11)    
    return geo, chip_pix, vlines, hlines

def io_channel_to_tile(io_channel):
    return int(np.floor((io_channel-1-((io_channel-1)%4))/4+1))

def tile_to_io_channel(tile):
    io_channel=[]
    for t in tile:
        for i in range(1,5,1): io_channel.append( ((t-1)*4)+i )
    return io_channel


def anode_xy(geo, chip_pix, vertical_lines, horizontal_lines, d, metric, normalization):
    if metric=='mean': metric=0
    if metric=='std': metric=1
    
    
    tile_dy = abs(max(vertical_lines))+abs(min(vertical_lines))
    tile_y_placement = [tile_dy*i for i in range(5)]
    mid_y = tile_y_placement[2]
    tile_y_placement = [typ-mid_y for typ in tile_y_placement]
    mid_vl = tile_dy/2.
    chip_y_placement = [typ+vl+mid_vl for typ in tile_y_placement[0:-1] \
                        for vl in vertical_lines[0:-1]]
    
    tile_dx = abs(max(horizontal_lines))+abs(min(horizontal_lines))
    tile_x_placement = [tile_dx*i for i in range(3)]
    mid_x = tile_x_placement[1]
    tile_x_placement = [txp-mid_x for txp in tile_x_placement]
    mid_hl = tile_dx/2.
    chip_x_placement = [txp+hl+mid_hl for txp in tile_x_placement[0:-1] \
                        for hl in horizontal_lines[0:-1]]
    
    fig, ax = plt.subplots(1,2,figsize=(16,16))
    for i in range(2):
        ax[i].set_title('Anode '+str(i+1))
        ax[i].set_xlim(tile_x_placement[0]*1.01,tile_x_placement[-1]*1.01)
        ax[i].set_ylim(tile_y_placement[0]*1.01,tile_y_placement[-1]*1.01)

        for typ in tile_y_placement:
            ax[i].hlines(y=typ, xmin=tile_x_placement[0],
                         xmax=tile_x_placement[-1], colors=['k'], \
                         linestyle='solid')

        for txp in tile_x_placement:
            ax[i].vlines(x=txp, ymin=tile_y_placement[0],
                         ymax=tile_y_placement[-1], colors=['k'], \
                         linestyle='solid')

        for cyp in chip_y_placement:
            ax[i].hlines(y=cyp, xmin=tile_x_placement[0], \
                         xmax=tile_x_placement[-1], colors=['k'], \
                         linestyle='dotted')
        for cxp in chip_x_placement:
            ax[i].vlines(x=cxp, ymin=tile_y_placement[0], \
                         ymax=tile_y_placement[-1], colors=['k'], \
                         linestyle='dotted')

    displacement={1:(-0.5,1.5), 2:(0.5,1.5), 3:(-0.5,0.5), 4:(0.5, 0.5), \
                  5:(-0.5,-0.5), 6:(0.5,-0.5), 7:(-0.5,-1.5), 8:(0.5,-1.5)}
    for i in range(1,9,1):
        io_channels=tile_to_io_channel([i])
        for chipid in chip_pix.keys():
            x,y = [[] for i in range(2)]
            for j in range(1,3,1):
                for ioc in io_channels:
                    chip_key=str(j)+'-'+str(ioc)+'-'+str(chipid)
                    if chip_key not in d: continue
                    for channelid in range(64):
                        if d[chip_key][channelid][0]==-1: continue
                        if i%2!=0:
                            xc = geo['pixels'][chip_pix[chipid][channelid]][1]
                            yc = geo['pixels'][chip_pix[chipid][channelid]][2]*-1
                        if i%2==0:
                            xc = geo['pixels'][chip_pix[chipid][channelid]][1]*-1
                            yc = geo['pixels'][chip_pix[chipid][channelid]][2]
                        xc += tile_dx*displacement[i][0]
                        yc += tile_dy*displacement[i][1]
                        weight=d[chip_key][channelid][metric]/normalization
                        if weight>1.: weight=1.0
                        r = Rectangle( ( xc-(pitch/2.), yc-(pitch/2.) ), pitch, \
                                   pitch, color='r', alpha=weight )

                        new_r = copy(r)
                        ax[j-1].add_patch(new_r)
            for channelid in range(64):
                if i%2!=0:        
                    x.append( geo['pixels'][chip_pix[chipid][channelid]][1] )
                    y.append( geo['pixels'][chip_pix[chipid][channelid]][2]*-1 )
                if i%2==0:        
                    x.append( geo['pixels'][chip_pix[chipid][channelid]][1]*-1 )
                    y.append( geo['pixels'][chip_pix[chipid][channelid]][2] )

            avgX = (max(x)+min(x))/2. + tile_dx*displacement[i][0]
            avgY = (max(y)+min(y))/2. + tile_dy*displacement[i][1]
            for j in range(2):
                ax[j].annotate(str(chipid), [avgX,avgY], ha='center', \
                               va='center', alpha=0.5)
#    fig.colorbar(cm.ScalarMappable(norm=Normalize(vmin=0, vmax=normalization),\
#                                   cmap='Reds'), ax=ax)

    return fig, ax



def main(geometry_path=_default_geometry_path, \
         input_json=_default_input_json, \
         file_prefix=_default_file_prefix, \
         metric=_default_metric, \
         normalization=_default_normalization, \
         **kwargs):
    if input_json==None:
        print('Provide JSON file. Exiting.')
        return
    if file_prefix==None:
        print('Provide output filename string. Exiting.')
        return
    
    d = dict()
    with open(input_json,'r') as f: d = json.load(f)
    
    geo, chip_pix, vertical_lines, horizontal_lines = load_yaml()
    
    fig, ax = anode_xy(geo, chip_pix, vertical_lines, horizontal_lines, d, metric, normalization)
    plt.tight_layout()
#    plt.show()
    plt.savefig(file_prefix+'-module2-anodes.png')
    return



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--geometry_path', default=_default_geometry_path, \
                        type=str, help='''Path to geometry YAML file''')
    parser.add_argument('--input_json', default=_default_input_json, \
                        type=str, help='''JSON-formatted dict oF \
                        chip_key:channel''')
    parser.add_argument('--file_prefix', default=_default_file_prefix, \
                        type=str, help='''String prepended to file''')
    parser.add_argument('--metric', default=_default_metric, \
                        type=str, help='''String of metric to plot\
                        'mean' or 'std' ''')
    parser.add_argument('--normalization', default=_default_normalization, \
                        type=float, help='''Float to normalize color scale''')
    #parser.add_arg
    args = parser.parse_args()
    main(**vars(args))
