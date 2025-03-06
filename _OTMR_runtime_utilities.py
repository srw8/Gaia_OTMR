import os
import shutil
import send_cmd as sc
import gethosts as get

class RunInfoAgg:
	'''RunInfoAgg
	A class to create a run_info object to extract all relevant data for analysis
	'''	
	def __init__(self, run_path):
		self.run_name = os.path.split(run_path)[1]
		self.run_dir = run_path
		self.ins_type = 'Gaia' ## TODO: how to discover?
		if self.ins_type == 'Gaia':
			
			## Run metadata
			self.run_type = 'OTMR' ## TODO: how to discover?
			self.run_date = self.run_name.split('_')[0]
			self.ins_id = self.run_name.split('_')[1]  
			self.run_id = self.run_name.split('_')[2]
			self.side = self.run_name.split('_')[3]
			self.surface = 'Top' ## TODO: how to discover?
			
			## Data locations
			## LLDs
			self.llds = []
			self.lld_dir = os.path.join(self.run_dir, r'LowLevelDiagnostics')
			if os.path.isdir(self.lld_dir):
				self.llds = [os.path.join(self.lld_dir, file) for file in os.listdir(self.lld_dir) if 'LLD' in file and '_0.csv' not in file]
			
			## Interop tables
			self.interops = []
			self.interop_dir = os.path.join(self.run_dir, r'InterOp')
			if os.path.isdir(self.interop_dir):
				self.interops = [os.path.join(self.interop_dir, file) for file in os.listdir(self.interop_dir) if '.bin' in file]
			
			## jitter files
			self.jitters = []
			self.jitter_dir = os.path.join(self.run_dir, r'Data\Metrics')
			if os.path.isdir(self.jitter_dir):
				for root, dirs, files in os.walk(self.jitter_dir):
					self.jitters.extend([os.path.join(root, file) for file in files if '.jitter' in file])

	def has(self):
		print(f'\nRun Info')
		print(f'{self.run_name}')
		print(f'{self.ins_id}')
		print(f'{self.surface}')
		print(f'{self.side}')		
		print('\nAvailable LLds:')
		for lld in self.llds: print(f'\t{os.path.join(os.path.split(os.path.split(lld)[0])[1],os.path.split(lld)[1])}')
		print('\nAvailable Interop:')
		for bin in self.interops: print(f'\t{os.path.join(os.path.split(os.path.split(bin)[0])[1],os.path.split(bin)[1])}')
		print('\nAvailable .jitter:')
		for jit in self.jitters: print(f'\t{os.path.join(os.path.split(os.path.split(jit)[0])[1],os.path.split(jit)[1])}')


def find_runs(method):
	home = os.path.dirname(__file__) #e.g. sftp://??.??.??.??/usr/local/illumina/scripts  
	run_dir = os.path.join(home, r'illumina/runs') #e.g. sftp://??.??.??.??/usr/local/illumina/runs
	run_list = sorted([_dir for _dir in os.listdir(run_dir) if os.path.isdir(_dir)], key=os.path.getctime)
	match method:
		case 'All' : 
			return run_list
		case 'Last': 
			return run_list[0]
		case _: 
			return []


def collect():
	home = os.path.dirname(__file__) #e.g. sftp://??.??.??.??/usr/local/illumina/scripts  
	source_dir = os.path.join(home, r'illumina/scripts') #e.g. sftp://??.??.??.??/usr/local/illumina/runs
	target_dir = os.path.join(find_runs('Last'),'LowLevelDiagnostics')
	
	if not os.path.isdir: 
		os.mkdir(target_dir)
	
	if os.path.isdir(source_dir):  
		llds = [os.path.join(source_dir, file) for file in os.listdir(source_dir) if 'LLD' in file]
	
	for lld in llds: 
		shutil.move(lld, os.path.join(target_dir))


def clean_lld_dir(lld_dir):
	save_dir = os.path.join(lld_dir, 'old')

	if not os.path.exists(save_dir): 
		os.mkdir(save_dir)
		llds = [os.path.join(lld_dir, f) for f in os.listdir(lld_dir) if '*.csv' in f]
	else:
		


def OTMR_LLD_init(IMB_IP, FCD_IP):

	## IMB init
	IMB_IP = '169.254.15.183'
	imb_cs, imb_ix = sc.build_up_connection(IMB_IP) # connect to the IMB
	sc.send_cmd(imb_ix, sc.create_ix_cmd("ix_x_lld_duration_set", duration_ms=2000)) ## xStage.LLD_IMB.PCA
	sc.send_cmd(imb_ix, sc.create_ix_cmd("ix_z_lld_duration_set", duration_ms=2000)) ## zStage.LLD_IMB.PCA
	imb_cs.close()
	imb_ix.close()


	##FCD init
	FCD_IP = '169.254.15.183'
	fcd_cs, fcd_ix = sc.build_up_connection(FCD_IP) # connect to the FCD
	sc.send_cmd(fcd_ix, sc.create_ix_cmd("ix_y_lld_duration_set", duration_ms=2000)) ## TipTiltFront.LLD_FCD.PCA
	sc.send_cmd(fcd_ix, sc.create_ix_cmd("ix_y_lld_duration_set", duration_ms=2000)) ## TipTiltRear.LLD_FCD.PCA
	sc.send_cmd(fcd_ix, sc.create_ix_cmd("ix_y_lld_duration_set", duration_ms=2000)) ## yStage.LLD_FCD.PCA
	fcd_cs.close()
	fcd_ix.close()