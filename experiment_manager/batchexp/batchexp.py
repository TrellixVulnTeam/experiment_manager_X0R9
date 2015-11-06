import uuid
import copy
from ..job_queue import get_jobqueue
from ..database import get_database
from ..job.experiment_job import ExperimentDBJob, GraphExpDBJob


class BatchExp(object):

	def __init__(self, name=None, jq_cfg = None, db_cfg=None, db=None, other_dbs=[], other_dbs_lookup=True, auto_job=True, virtual_env=None, requirements=[], **kwargs):
		self.uuid = str(uuid.uuid1())
		if name is None:
			self.name = self.uuid
		else:
			self.name = name
		if jq_cfg == None:
			self.jq_cfg = {'jq_type':'local'}
		else:
			self.jq_cfg = jq_cfg
		if 'name' not in self.jq_cfg.keys():
			self.jq_cfg['name'] = self.name
		self.jobqueue = get_jobqueue(**self.jq_cfg)
		if db is not None:
			self.db = db
		elif db_cfg is not None:
			self.db = get_database(**db_cfg)
		else:
			self.db = get_database(**{'db_type':'sqlite','name':self.name})
		self.other_dbs = other_dbs
		self.other_dbs_lookup = other_dbs_lookup
		self.auto_job = auto_job
		self.virtual_env = virtual_env
		self.requirements = requirements
#	def control_exp(self, exp):
#		exp.originclass = copy.deepcopy(exp.__class__)
#		exp.__class__ = Experiment
#		exp._batch_exp = self
#
#	def uncontrol_exp(self, exp):
#		exp.__class__ = exp.originclass
#		delattr(exp,'_batch_exp')
#		delattr(exp,'originclass')

	def get_experiment(self, uuid=None, force_new=False, blacklist=[], pattern=None, tmax=0, auto_job=True, **xp_cfg):
		exp = self.db.get_experiment(uuid=uuid, force_new=force_new, blacklist=blacklist, pattern=pattern, tmax=tmax, **xp_cfg)
#		self.control_exp(exp)
		if auto_job and exp._T[-1] < tmax:
			self.add_exp_job(uuid=exp.uuid, tmax=tmax)
			print 'added job for exp {}, from {} to {}'.format(uuid, exp._T[-1], tmax)
		return exp

	def get_graph(self, uuid, method, tmin=0, tmax=None):
		if self.db.data_exists(uuid=uuid, method=method):
			graph = self.db.get_graph(uuid=uuid, method=method)
			return graph
#		self.control_exp(exp)
		if self.auto_job and exp._T[-1] < tmax:
			self.add_graph_job(uuid=exp.uuid, method=method, tmax=tmax)
			print 'added graph job for exp {}, method {} to {}'.format(uuid, method, tmax)

	def add_exp_job(self, tmax, uuid=None, xp_cfg=None):
		exp = self.get_experiment(uuid=uuid, **xp_cfg)
		if not exp._T[-1]>=tmax:
			job = ExperimentDBJob(exp=exp, T=tmax, virtual_env=self.virtual_env, requirements=self.requirements)
			self.jobqueue.add_job(job)

	def add_graph_job(self, method, uuid=None, tmax=None, xp_cfg=None):
		exp = self.get_experiment(uuid=uuid, **xp_cfg)
		job = GraphExpDBJob(exp=exp, method=method, tmax=tmax, virtual_env=self.virtual_env, requirements=self.requirements)
		self.jobqueue.add_job(job)

	def add_jobs(self, cfg_list):
		for cfg in cfg_list:
			if 'uuid' in cfg.keys():
				nb_iter = 1
			elif 'nb_iter' not in cfg.keys():
				nb_iter = 1
			else:
				nb_iter = cfg['nb_iter']
			blacklist = []
			for i in range(nb_iter):
				if 'uuid' not in cfg.keys():
					exp = self.db.get_experiment(blacklist=blacklist, **cfg['xp_cfg'])
					uuid = exp.uuid
					blacklist.append(uuid)
				else:
					uuid = cfg['uuid']
				cfg2 = dict((k,cfg[k]) for k in ('uuid', 'xp_cfg', 'method', 'tmax') if k in cfg.keys())
				if 'method' in cfg.keys():
					self.add_graph_job(**cfg2)
				else:
					self.add_exp_job(**cfg2)

	def update_queue(self):
		self.jobqueue.update_queue()

	def auto_finish_queue(self,t=60):
		self.jobqueue.auto_finish_queue(t=60)

#class Experiment(object):
#
#	def __getattr__(self, attr):
#		forbidden = ['originclass','_batch_exp', 'commit_to_db', 'commit_data_to_db', 'continue_exp_until', 'graph']
#		if attr not in forbidden:
#			return self.originclass.__getattr__(self, attr)
#		else:
#			return self.__getattribute__(self, attr)
#
#	def continue_exp_until(self):
#
#	def graph(self):
#
#	def commit_to_db(self, *args, **kwargs):
#		exp = copy.deepcopy(self)
#		self._batch_exp.uncontrol_exp(exp)
#		exp.commit_to_db(*args, **kwargs)
#
#	def commit_data_to_db(self, *args, **kwargs):
#		exp = copy.deepcopy(self)
#		self._batch_exp.uncontrol_exp(exp)
#		exp.commit_data_to_db(*args, **kwargs)
#