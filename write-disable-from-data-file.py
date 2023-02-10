# Written by Stephen Greenberg, stephen_greenberg@berkeley.edu

import h5py
import json
import argparse

_default_input_file=None
_default_file_prefix=None
runtime=1
# ORIGINAL
#data_file = '/data/LArPix/Module2_Nov2022/commission/Nov16/trial0-packet-2022_11_16_21_57_CET.h5'
all_rates = []
def main(input_file=_default_input_file, \
		 file_prefix=_default_file_prefix,\
		 **kwargs):
	if input_file==None:
		print('Provide an input HDF5 packet file. Exiting.')
		return
	if file_prefix==None:
		print('Provide a filename for ouptut file. Exiting.')
		return
	f = h5py.File(input_file)
	packets = f['packets'][f['packets']['packet_type']==0]
	total_n_packets = len(packets)
	print('total packets read:', total_n_packets)
	disable = {}
	count=0
	total_channels = 0
	for iog in set(packets['io_group']):
		_packets = packets[packets['io_group']==iog]
		for ioch in set(_packets['io_channel']):
			__packets = _packets[_packets['io_channel']==ioch]
			for chid in set(__packets['chip_id']):
				data = __packets[__packets['chip_id']==chid]
				key = '{}-{}-{}'.format(iog, ioch, chid)
				for channel in set(data['channel_id']):
					dpm = data['channel_id']==channel
					total_channels += 1
					all_rates.append(sum(dpm.astype(int))/total_n_packets)
					if sum(dpm.astype(int))/total_n_packets >0.00001: #this channel accounts for more than 0.1% of total rate (avg should be 0.001%)
						count+=1
						print(key, channel, '\t rate fraction:', sum(dpm.astype(int))/total_n_packets)
						if key in disable: disable[key].append(int(channel))
						else: disable[key]=[int(channel)]

	#print(disable)
	print('disabled', count, 'out of', total_channels, 'channels')
	with open(file_prefix+'-disable.json', 'w') as ff:
		json.dump(disable, ff)

	from matplotlib import pyplot as plt
	fig = plt.figure()
	ax = fig.add_subplot()
	ax.hist(all_rates, bins=5000)
	ax.set_yscale('log')
	plt.show()

if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--input_file', default=_default_input_file, \
			type=str, help='''Input HDF5 pakcet file''')
	parser.add_argument('--file_prefix', default=_default_file_prefix, \
						type=str, help='''String prepended to file''')
	args = parser.parse_args()
	main(**vars(args))
