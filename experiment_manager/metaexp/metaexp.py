import copy
import numpy as np
from scipy.optimize import curve_fit

from ..batchexp.batchexp import BatchExp

def dbcheck(func):
	def dbcheckobj(obj_self,*args,**kwargs):
		if obj_self.db is None:
			raise ValueError('No database set, please use set_db method to set it')
		else:
			return func(obj_self,*args,**kwargs)
	return dbcheckobj

def number_str(number):
	try:
		return str(round(number,int(-round(np.log10(number))+2)))
	except:
		return 'NaN'

def powerlaw_loglogfit(X,Y):
	def powerlaw(logx,A,k):
		return np.log(A) + k*logx
	index_list = [index for index in range(len(Y)) if np.isfinite(Y[index])]
	_Y = [Y[i] for i in index_list]
	_X = [X[i] for i in index_list]
	logX = np.log(_X)
	logY = np.log(_Y)
	init_vals = [1, 0]
	if len(logY) < 2:
		best_vals = np.array(init_vals)
	elif len(logY) == 2:
		_k = np.log(_Y[0]/float(_Y[1]))/np.log(_X[0]/float(_X[1]))
		_A = _Y[0]/float(_X[0]**_k)
		best_vals = (_A,_k)
	else:
		try:
			best_vals, covar = curve_fit(powerlaw, xdata=logX, ydata=logY, p0=init_vals)
		except ValueError:
			raise ValueError(str(logX)+'\n'+str(logY)+'\n'+str(X)+'\n'+str(Y)+'\n'+str(_X)+'\n'+str(_Y))
	logY_fit = powerlaw(logX,*best_vals)
	logYbar = np.sum(logY)/len(logY)
	ssreg = np.sum((logY_fit-logYbar)**2)
	sstot = np.sum((logY - logYbar)**2)
	r2 = ssreg / sstot
	return best_vals, r2

class MetaExperiment(object):
	def __init__(self,params,local_measures,global_measures,xp_cfg,Tmax_func,default_nbiter=1,time_label='Time',time_short_label='t'):
		self.params = copy.deepcopy(params)
		self.local_measures = copy.deepcopy(local_measures)
		self.global_measures = copy.deepcopy(global_measures)
		self._xp_cfg = copy.deepcopy(xp_cfg)
		self._Tmax_func = copy.deepcopy(Tmax_func)
		self.default_nbiter = default_nbiter
		self.db = None
		self.time_label = time_label
		self.time_short_label = time_short_label
		self.default_batch = 'nobatch'
		self.batches = {'nobatch':'nobatch'}
		self.measures = list(self.local_measures.keys()) + list(self.global_measures.keys())

		for k,v in list(self.params.items()):
			test1 = 'default_value' not in list(self.params[k].keys())
			test2 = 'values' not in list(self.params[k].keys())
			if test1 and test2:
				raise ValueError('No values or default value provided for parameter '+str(k))
			elif test1:
				self.params[k]['default_value'] = copy.deepcopy(self.params[k]['values'][0])
			elif test2:
				self.params[k]['values'] = [copy.deepcopy(self.params[k]['default_value'])]
			if 'label' not in list(self.params[k].keys()):
				self.params[k]['label'] = str(k)
			if 'short_label' not in list(self.params[k].keys()):
				self.params[k]['short_label'] = str(k)
			if 'unit_label' not in list(self.params[k].keys()):
				self.params[k]['unit_label'] = self.params[k]['short_label']
			if 'min' not in list(self.params[k].keys()):
				self.params[k]['min'] = min(copy.deepcopy(self.params[k]['values']))
			if 'max' not in list(self.params[k].keys()):
				self.params[k]['max'] = max(copy.deepcopy(self.params[k]['values']))

	def complete_params(self,subparams,allow_list=False):
		_subparams = copy.deepcopy(subparams)
		if allow_list:
			for k,v in list(self.params.items()):
				if k not in list(_subparams.keys()):
					_subparams[k] = copy.deepcopy(v['default_value'])
				if _subparams[k] == 'all':
					_subparams[k] = copy.deepcopy(self.params[k]['values'])
				if _subparams[k] == 'first':
					_subparams[k] = copy.deepcopy(self.params[k]['values'][0])
				elif _subparams[k] == 'last':
					_subparams[k] = copy.deepcopy(self.params[k]['values'][-1])
		else:
			for k,v in list(self.params.items()):
				if k not in list(_subparams.keys()):
					_subparams[k] = copy.deepcopy(v['default_value'])
				if _subparams[k] == 'first':
					_subparams[k] = copy.deepcopy(self.params[k]['values'][0])
				elif _subparams[k] == 'last':
					_subparams[k] = copy.deepcopy(self.params[k]['values'][-1])
				if isinstance(_subparams[k],list):
					raise TypeError('Parameter '+str(k)+' was provided several values instead of one: '+str(_subparams[k]))
				if _subparams[k] == 'all':
					raise TypeError('Parameter '+str(k)+' was provided several values instead of one: '+str(v['values']))
		return _subparams

	def Tmax(self,**subparams):
		_subparams = self.complete_params(subparams,allow_list=False)
		return self._Tmax_func(**_subparams)

	def xp_cfg(self,**subparams):
		_subparams = self.complete_params(subparams,allow_list=False)
		return self._xp_cfg(**_subparams)

	def set_db(self,db):
		self.db = db

	@dbcheck
	def plot(self,measure,nbiter=None,get_object=False,**subparams):
		if nbiter is None:
			nbiter = self.default_nbiter
		try:
			_subparams = self.complete_params(subparams,allow_list=False)
		except TypeError:
			return self.plot_several(measure=measure,nbiter=nbiter,get_object=get_object,**subparams)
			#raise ValueError('Parameter '+str(k)+' has several values: '+str(_subparams[k])+'. Use plot_several to use different parameter values.')
		cfg = self.xp_cfg(**_subparams)
		xp_uuid = self.db.get_graph_id_list(method=measure,xp_cfg=cfg)[:nbiter]
		if len(xp_uuid)<nbiter:
			raise ValueError('Only '+str(len(xp_uuid))+' experiments available in the database, nbiter=' +str(nbiter)+ ' asked')
		gr = self.db.get_graph(method=measure,xp_uuid=xp_uuid[0])
		for i in range(nbiter-1):
			gr.add_graph(self.db.get_graph(method=measure,xp_uuid=xp_uuid[i+1]))
		gr.merge()
		try:
			gr.title = self.local_measures[measure]['label']
			if 'unit_label' in list(self.local_measures[measure].keys()):
				gr.ylabel = self.local_measures[measure]['unit_label']
		except:
			try:
				gr.title = self.global_measures[measure]['label']
				if 'unit_label' in list(self.global_measures[measure].keys()):
					gr.ylabel = self.global_measures[measure]['unit_label']
			except:
				gr.title = measure
		gr.xlabel = self.time_label
		if get_object:
			return gr
		else:
			gr.show()

	@dbcheck
	def plot_single(self,*args,**kwargs):
		return self.plot(*args,nbiter=1,**kwargs)

	@dbcheck
	def plot_against_single(self,*args,**kwargs):
		return self.plot_against(*args,nbiter=1,**kwargs)


	@dbcheck
	def plot_several(self,measure,nbiter=None,get_object=False,**subparams):
		if nbiter is None:
			nbiter = self.default_nbiter
		_subparams = self.complete_params(subparams,allow_list=True)
		varying_params = []
		for k in list(_subparams.keys()):
			if isinstance(_subparams[k],list):
				varying_params.append(k)
		configs = []
		if varying_params == []:
			return self.plot(measure=measure,nbiter=nbiter,get_object=get_object,**subparams)
		for k in varying_params:
			if configs == []:
				configs = [{k:v} for v in _subparams[k]]
			else:
				configs_bis = []
				for c in configs:
					for v in _subparams[k]:
						c2 = copy.deepcopy(c)
						c2[k] = v
						configs_bis.append(c2)
				configs = configs_bis
		_subparams_bis = copy.deepcopy(_subparams)
		_subparams_bis.update(configs[0])
		gr = self.plot(measure=measure,get_object=True,nbiter=nbiter,**_subparams_bis)
		if len(configs) > 1:
			for c in configs[1:]:
				_subparams_bis = copy.deepcopy(_subparams)
				_subparams_bis.update(c)
				gr2 = self.plot(measure=measure,get_object=True,nbiter=nbiter,**_subparams_bis)
				gr.add_graph(gr2)
		gr.legendoptions['labels'] = [', '.join([self.params[k]['short_label']+'='+str(c[k]) for k in varying_params]) for c in configs]
		if get_object:
			return gr
		else:
			gr.show()

	@dbcheck
	def plot_against(self,token,measure,nbiter=None,get_object=False,**subparams):
		if not token in self.params.keys():
			raise ValueError('Unknown parameter: '+str(token))
		if token not in list(subparams.keys()) or subparams[token] == 'all':
			token_values = copy.deepcopy(self.params[token]['values'])
		else:
			token_values = copy.deepcopy(subparams[token])
		_subparams = copy.deepcopy(subparams)
		_subparams[token] = token_values[0]
		gr = self.plot(measure=measure,nbiter=nbiter,get_object=True,**_subparams)
		for i in range(len(gr._X)):
			gr._X[i][0] = _subparams[token]
		for v in token_values[1:]:
			_subparams = copy.deepcopy(subparams)
			_subparams[token] = v
			gr2 = self.plot(measure=measure,nbiter=nbiter,get_object=True,**_subparams)
			for i in range(len(gr2._X)):
				gr2._X[i][0] = _subparams[token]
			gr.complete_with(gr2)
		gr.xlabel = self.params[token]['unit_label']
		gr.xmin = self.params[token]['min']
		gr.xmax = self.params[token]['max']
		if get_object:
			return gr
		else:
			gr.show()


	@dbcheck
	def plot_bestparam(self,xtoken,ytoken,measure,type_optim,nbiter=None,get_object=False,get_vect=False,**subparams):
		sp = copy.deepcopy(subparams)
		for k in list(sp.keys()):
			if k not in [xtoken,ytoken] and (isinstance(sp[k],list) or sp[k] == 'all'):
				return self.plot_bestparam_several(xtoken=xtoken,ytoken=ytoken,measure=measure,type_optim=type_optim,nbiter=nbiter,get_object=get_object,get_vect=get_vect,**sp)
				#TODO: get_vect for plot_bestparam_several
		gr = self.plot_against(token=xtoken,measure=measure,nbiter=nbiter,get_object=True,**sp)
		assert type_optim in ['min','max']
		if ytoken not in list(subparams.keys()) or subparams[ytoken] == 'all':
			yvec = self.params[ytoken]['values']
		else:
			yvec = subparams[ytoken]
		best_param_vect = []
		#TODO: handle case with different _X vectors
		for gx in gr._X:
			assert gx == gr._X[0]
		for x in range(len(gr._X[0])):
			if type_optim == 'min':
				val = min([gr._Y[i][x] for i in range(len(gr._Y))])
			elif type_optim == 'max':
				val = max([gr._Y[i][x] for i in range(len(gr._Y))])
			y_v = [i for i in range(len(gr._Y)) if gr._Y[i][x]==val]
			if y_v:
				y = y_v[0]
			else:
				y = 0
			best_param_vect.append(yvec[y])
		if get_vect:
			return best_param_vect
		gr2 = copy.deepcopy(gr)
		gr2.merge()
		gr2.ymin = self.params[ytoken]['min']#min(yvec)
		gr2.ymax = self.params[ytoken]['max']#max(yvec)
		if 'labels' in list(gr2.legendoptions.keys()):
			del gr2.legendoptions['labels']
		gr2.stdvec = [[0 for _ in best_param_vect]]
		gr2._Y[0] = best_param_vect
		try:
			mm = self.global_measures[measure]['label']
		except:
			mm = measure
		gr2.title = 'Best '+self.params[ytoken]['label']+' '+type_optim+'imizing '+ mm
		gr2.ylabel = self.params[ytoken]['unit_label']
		if get_object:
			return gr2
		else:
			gr2.show()

	@dbcheck
	def plot_bestparam_several(self,xtoken,ytoken,measure,type_optim,nbiter=None,get_object=False,get_vect=False,**subparams):
		if nbiter is None:
			nbiter = self.default_nbiter
		_subparams = self.complete_params(subparams,allow_list=True)
		print(_subparams)
		varying_params = []
		for k in list(_subparams.keys()):
			if isinstance(_subparams[k],list):
				varying_params.append(k)
		configs = []
		if xtoken not in subparams:
			_subparams[xtoken] = self.params[xtoken]['values']
		if ytoken not in subparams:
			_subparams[ytoken] = self.params[ytoken]['values']
		if varying_params == []:
			return self.plot_bestparam(xtoken=xtoken,ytoken=ytoken,measure=measure,type_optim=type_optim,nbiter=nbiter,get_object=get_object,**_subparams)
		for k in varying_params:
			if configs == []:
				configs = [{k:v} for v in _subparams[k]]
			else:
				configs_bis = []
				for c in configs:
					for v in _subparams[k]:
						c2 = copy.deepcopy(c)
						c2[k] = v
						configs_bis.append(c2)
				configs = configs_bis
		_subparams_bis = copy.deepcopy(_subparams)
		_subparams_bis.update(configs[0])
		gr = self.plot_bestparam(xtoken=xtoken,ytoken=ytoken,measure=measure,type_optim=type_optim,get_object=True,nbiter=nbiter,**_subparams_bis)
		if len(configs) > 1:
			for c in configs[1:]:
				_subparams_bis = copy.deepcopy(_subparams)
				_subparams_bis.update(c)
				gr2 = self.plot_bestparam(xtoken=xtoken,ytoken=ytoken,type_optim=type_optim,measure=measure,get_object=True,nbiter=nbiter,**_subparams_bis)
				gr.add_graph(gr2)
		gr.legendoptions['labels'] = [', '.join([self.params[k]['short_label']+'='+str(c[k]) for k in varying_params]) for c in configs]
		if get_object:
			return gr
		else:
			gr.show()

	@dbcheck
	def run(self,batch=None,t=10,coeff=2,nbiter=None,**subparams):
		if nbiter is None:
			nbiter = self.default_nbiter
		_subparams = copy.deepcopy(subparams)
		for k in list(self.params.keys()):
			if k not in list(_subparams.keys()) or _subparams[k]=='all':
				_subparams[k] = copy.deepcopy(self.params[k]['values'])
			if not isinstance(_subparams[k],list):
				_subparams[k] = [_subparams[k]]
		if batch is None:
			batch = self.batches[self.default_batch]
		if batch == 'nobatch':
			configs = []
			for k in list(_subparams.keys()):
				if configs == []:
					configs = [{k:v} for v in _subparams[k]]
				else:
					configs_bis = []
					for c in configs:
						for v in _subparams[k]:
							c2 = copy.deepcopy(c)
							c2[k] = v
							configs_bis.append(c2)
					configs = configs_bis
			cfg_list = [self.xp_cfg(**c) for c in configs]
			for cfg,c in zip(cfg_list,configs):
				id_list = self.db.get_id_list(**cfg)
				if len(id_list)<nbiter:
					for i in range(nbiter-len(id_list)):
						xp = self.db.get_experiment(force_new=True,**cfg)
						id_list.append(xp.uuid)
				for xp_uuid in id_list:
					test = self.db.get_param(xp_uuid=xp_uuid, param='Tmax')>=self.Tmax(**c)
					for m in list(self.local_measures.keys())+list(self.global_measures.keys()):
						test = test and self.db.data_exists(xp_uuid=xp_uuid, method=m)
						test = test and self.db.get_param(xp_uuid=xp_uuid, param='Time_max',method=m)>=self.Tmax(**c)
					if not test:
						xp = self.db.get_experiment(xp_uuid=xp_uuid)
						xp.continue_exp_until(T=self.Tmax(**c))
						for m in  list(self.local_measures.keys())+list(self.global_measures.keys()):
							xp.graph(method=m)
		else:
			job_configs = []
			for k in list(_subparams.keys()):
				if job_configs == []:
					job_configs = [{k:v} for v in _subparams[k]]
				else:
					configs_bis = []
					for c in job_configs:
						for v in _subparams[k]:
							c2 = copy.deepcopy(c)
							c2[k] = v
							configs_bis.append(c2)
					job_configs = configs_bis
			job_cfg_list = [{'xp_cfg':self.xp_cfg(**c),'method': list(self.local_measures.keys())+list(self.global_measures.keys()),'tmax':self.Tmax(**c),'nb_iter':nbiter} for c in job_configs]
			batch.add_jobs(job_cfg_list)
			batch.jobqueue.auto_finish_queue(t=t,coeff=coeff)
			#TODO: clear output

	def run_single(self,batch=None):
		self.run(batch=batch,nbiter=1)

	@dbcheck
	def set_batch(self,name=None,set_as_default=False,**batch_cfg):
		_batch_cfg = copy.deepcopy(batch_cfg)
		if name is None:
			try:
				name = _batch_cfg['name']
			except:
				name = _batch_cfg['jq_cfg']['jq_type']
		elif not _batch_cfg:
			_batch_cfg['jq_cfg']={'jq_type':name}
		self.batches[name] = BatchExp(db=self.db,**_batch_cfg)
		if set_as_default:
			self.default_batch = name

	def powerlaw_fit(self,graph,get_object=False,get_values=False,display_mode=None,use_formula=False):
		gr = copy.deepcopy(graph)
		if 'labels' in list(graph.legendoptions.keys()) and len(graph.legendoptions['labels']) == len(graph._X):
			labels = copy.deepcopy(graph.legendoptions['labels'])
		else:
			labels = ['' for _ in graph._X]
		if display_mode=='2columns':
			gr.legendoptions['labels'] = labels
		else:
			gr._X = []
			gr._Y = []
			gr.Yoptions = []
			gr.stdvec = []
			gr.legendoptions['labels'] = []
		for i in range(len(graph._X)):
			x = copy.deepcopy(graph._X[i])
			y = copy.deepcopy(graph._Y[i])
			params,r2 = powerlaw_loglogfit(x,y)
			y_fit = params[0]*np.power(x,params[1])
			if not display_mode=='2columns':
				gr._X.append(copy.deepcopy(x))
				gr._Y.append(copy.deepcopy(y))
				gr.stdvec.append(copy.deepcopy(graph.stdvec[i]))
				gr.Yoptions.append(copy.deepcopy(graph.Yoptions[i]))
				gr.legendoptions['labels'].append(labels[i])
			else:
				gr.legendoptions['ncol'] = 2
			gr._X.append(copy.deepcopy(x))
			gr._Y.append(copy.deepcopy(y_fit))
			gr.stdvec.append([0]*len(x))
			options = copy.deepcopy(graph.Yoptions[i])
			options['linestyle'] = '--'
			options['color'] = 'black'
			gr.Yoptions.append(options)
			gr.loglog = True
			if gr.ylabel is not None and (len(gr.ylabel)<4 or (gr.ylabel[:2]=='$\\' and gr.ylabel[-1] == '$')):
				y_symbol = gr.ylabel
			else:
				y_symbol = 'y'
			if gr.xlabel is not None and (len(gr.xlabel)<4 or (gr.xlabel[:2]=='$\\' and gr.xlabel[-1] == '$')):
				x_symbol = gr.xlabel
			else:
				x_symbol = 'x'
			if use_formula:
				gr.legendoptions['labels'].append(y_symbol+'='+number_str(params[0])+'$\\cdot$'+x_symbol+'$^{'+number_str(params[1])+'}$, R$^2$='+number_str(r2))
			else:
				gr.legendoptions['labels'].append(y_symbol+'='+number_str(params[0])+'*'+x_symbol+'^'+number_str(params[1])+', R^2='+number_str(r2))
			#gr.legendoptions['labels'].append(y_symbol+'='+number_str(params[0])+r'$\cdot$'+x_symbol+'^{'+number_str(params[1])+'}, R^2='+number_str(r2))
		if not get_values and not get_object:
			gr.show()
		elif get_object:
			return gr
		elif get_values:
			return params,r2
		else:
			raise ValueError('get_object and get_values cannot be set to True at the same time.')
