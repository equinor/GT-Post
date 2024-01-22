# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 13:28:39 2016

@author: Liang
"""
import os
import numpy as np


class PreProcessHelper:
    # Retrieve the rendered values from the files
    destination = os.path.join('/', 'data', 'output')
    #destination = 'c:\\Users\\Liang\\dockertest\\preprocess-task-515\\docker\\results\\'
    composition = 'medium-sand'

    def getbcc(self):
        filename = 'a.bcc'
        bccfile = os.path.join(self.destination, filename)
        bcc = {'t_stop': None}
        tstop_value = []
        # retrieve the tstop
        with open(bccfile, 'r') as f:
            alllines=f.readlines()
            nlines = [alllines[x] for x in range(12,104,13)]
            lnline = len(nlines)
            for lines in range(lnline):
                tstop_res = float(nlines[lines].split()[0])
                tstop_value.append(tstop_res)
        bcc.update({'t_stop': tstop_value})
        return bcc
        
    def getbch(self):
        filename = 'a.bch'
        bchfile = os.path.join(self.destination, filename)
        bch = {'T_amplitude': None,
               'baselevel_degree': None,
               'baselevel_change': None,
               'baselevel_phase': None}
        tidal_value = []
        base_level_change_value = []
        base_level_phase_value =[]
        with open(bchfile, 'r') as f:
            alllines=f.readlines()
            # retrieve the tidal amplitude             
            nlines = [alllines[x] for x in range(4,8,3)]
            lnline = len(nlines)
            for lines in range(lnline):
                tidal_amplitude = float(nlines[lines].split()[0])                      
                tidal_value.append(tidal_amplitude)
            # retrieve the base-level degree
            firstline = alllines[0]
            base_level_degree = float(firstline.split()[-1])
            # retrieve the base-level change
            nlines = [alllines[x] for x in range(4,8,3)]
            lnline = len(nlines)
            for lines in range(lnline):
                base_level_change = float(nlines[lines].split()[-1])                      
                base_level_change_value.append(base_level_change)
            # retrieve the base-level phase
            nlines = [alllines[x] for x in range(11,15,3)]
            lnline = len(nlines)
            for lines in range(lnline):
                base_level_phase = float(nlines[lines].split()[-1])                      
                base_level_phase_value.append(base_level_phase)                
        bch.update({'T_amplitude': tidal_value, 
                   'baselevel_degree': base_level_degree,
                   'baselevel_change': base_level_change_value,
                   'baselevel_phase': base_level_phase_value})
        return bch

    def getbct(self):
        filename = 'a.bct'
        bctfile = os.path.join(self.destination, filename)
        bct = {'t_stop': None,
               'river_discharge': None}
        riverdischarge_value = []
        with open(bctfile, 'r') as f:
            alllines=f.readlines()
            # retrieve the tstop
            tstop_value = float(alllines[-1].split()[0])                      
            # retrieve the river discharge
            riverdischarge = float(alllines[-1].split()[1])
            riverdischarge1 = float(alllines[-2].split()[1])
            riverdischarge_value.append(riverdischarge)
            riverdischarge_value.append(riverdischarge1)        
        bct.update({'t_stop': tstop_value, 
                   'river_discharge': riverdischarge_value})
        return bct
        
    def getbnd(self):
        filename = 'a.bnd'
        bndfile = os.path.join(self.destination, filename)
        bnd = {'River_u': None,
               'River_l': None}
        with open(bndfile, 'r') as f:
            alllines=f.readlines()
            # retrieve the river boundary location
            river_u = float(alllines[-1].split()[-3])                      
            river_l = float(alllines[-1].split()[-5])                      
        bnd.update({'River_u': river_u, 
                   'River_l': river_l})
        return bnd
    
    def getmor(self):
        # the morfac is only changed for the wave template
        filename = 'a.mor'
        morfile = os.path.join(self.destination, filename)
        mor = {'mor': None}
        with open(morfile, 'r') as f:
            for lines in f.readlines():
                if 'MorFac' in lines:
                    morvalue = float(lines.split()[2])                   
        mor.update({'mor': morvalue})
        return mor
    
    def getmdf(self):
        filename = '%s.mdf' % self.composition
        mdffile = os.path.join(self.destination, filename)       
        mdf = {'t_stop': None,
               't_dt': None,
               't_start': None,
               't_interval': None}
        tstop_value = []
        tstart_value = []
        t_interval_value = []
        with open(mdffile, 'r') as f:
            for lines in f.readlines():
                # retieve tstop value
                if 'Tstop' in lines:
                    tstop = float(lines.split()[-1])
                    tstop_value.append(tstop)
                if 'Dt' in lines:
                    dt = float(lines.split()[-1])
                if 'Flmap' in lines:
                    tstop = float(lines.split()[-1])
                    tstop_value.append(tstop)
                    t_interval = float(lines.split()[-2])
                    t_interval_value.append(t_interval)
                    t_start = float(lines.split()[-3])
                    tstart_value.append(t_start)
                if 'Flhis' in lines:
                    tstop = float(lines.split()[-1])
                    tstop_value.append(tstop)
                    t_interval = float(lines.split()[-2])
                    t_interval_value.append(t_interval)
                    t_start = float(lines.split()[-3])
                    tstart_value.append(t_start)
                if 'Flpp' in lines:
                    tstop = float(lines.split()[-1])
                    tstop_value.append(tstop)
                    t_start = float(lines.split()[-3])
                    tstart_value.append(t_start)                                           
        mdf.update({'t_stop': tstop_value,
                      't_dt': dt,
                      't_start': tstart_value,
                      't_interval': t_interval_value})
        return mdf              

    def getmdw(self):
        filename = 'wave.mdw'
        mdwfile = os.path.join(self.destination, filename)
        mdw = {'waveheight': None}
        with open(mdwfile, 'r') as f:
            for lines in f.readlines():
                if 'WaveHeight' in lines:
                    waveheightvalue = float(lines.split()[2])                   
        mdw.update({'waveheight': waveheightvalue})
        return mdw

    def getdep(self):
        filename = 'a.dep'
        depfile = os.path.join(self.destination, filename)
        dep = np.loadtxt(depfile)
        return dep
               
if __name__ == '__main__':
    #unittest.main()
    PP = PreProcessHelper()
    bcc = PP.getbcc()
    bch = PP.getbch()
    bct = PP.getbct()
    bnd = PP.getbnd()
    mor = PP.getmor()    
    mdf = PP.getmdf()
    mdw = PP.getmdw()    