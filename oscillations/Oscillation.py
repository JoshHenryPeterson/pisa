#! /usr/bin/env python
#
# Oscillation.py
#
# This module is the implementation of the physics oscillation step.
# The main purpose of this step is to produce oscillation probability
# maps of each neutrino flavor into the others, for a given set of
# oscillation parameters, and to multiply it by the corresponding flux
# map, producing oscillated flux maps.
#
# author: Timothy C. Arlen
#         tca3@psu.edu
#
# date:   Jan. 21, 2014
#


## IMPORTS ##
import os,sys
import numpy as np
import logging
import inspect
from argparse import ArgumentParser, RawTextHelpFormatter
from utils.utils import set_verbosity,is_equal_binning
from utils.jsons import from_json, to_json
from OscillationService import OscillationService

# Until python2.6, default json is very slow.
try: 
    import simplejson as json
except ImportError, e:
    import json


def get_osc_flux(flux_maps,osc_service=None,deltam21=None,deltam31=None,theta12=None,
                 theta13=None,theta23=None,deltacp=None,**kwargs):
    '''
    Uses osc_prob_maps to calculate the oscillated flux maps.
    Inputs:
      flux_maps - dictionary of atmospheric flux ['nue','numu','nue_bar','numu_bar']
      osc_service - a handle to an OscillationService
      others - oscillation parameters to compute oscillation probability maps from.
    '''

    #Get list of arguments and values dict, ignoring *varargs and **kwargs 
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    units = ['eV^2','eV^2','rad','rad','rad','rad']
    #Print all parameters but the first two
    for param, unit in zip(args[2:],units):
        logging.debug("%10s: %.4e %s"%(param,values[param],unit))
    
    #Get oscillation probability map from service
    osc_prob_maps = osc_service.get_osc_prob_maps(deltam21,deltam31,theta12,
                                                  theta13,theta23,deltacp)
    
    osc_flux_maps = {}
    for to_flav in ['nue','numu','nutau']:
        for mID in ['','_bar']: # 'matter' ID
            nue_flux = flux_maps['nue'+mID]['map']
            numu_flux = flux_maps['numu'+mID]['map']
            oscflux = {'ebins':ebins,
                       'czbins':czbins,
                       'map':(nue_flux*osc_prob_maps['nue'+mID+'_maps'][to_flav+mID] +
                              numu_flux*osc_prob_maps['numu'+mID+'_maps'][to_flav+mID])
                       }
            osc_flux_maps[to_flav+mID] = oscflux
            
    return osc_flux_maps

        
if __name__ == '__main__':
    
    #Only show errors while parsing
    set_verbosity(0)

    # parser
    parser = ArgumentParser(description='Takes the oscillation parameters '
                            'as input and writes out a set of osc flux maps',
                            formatter_class=RawTextHelpFormatter)    
    parser.add_argument('flux_file',metavar='FLUX',type=from_json,
                        help='''JSON atm flux input file with the following parameters:
    {"nue": {'czbins':[], 'ebins':[], 'map':[]},
     "numu": {...},
     "nue_bar": {...},
     "numu_bar":{...}}''')
    parser.add_argument('--deltam21',type=float,default=7.54e-5,
                        help='''deltam21 value [eV^2]''')
    parser.add_argument('--deltam31',type=float,default=0.00246,
                        help='''deltam31 value [eV^2]''')
    parser.add_argument('--theta12',type=float,default=0.5873,
                        help='''theta12 value [rad]''')
    parser.add_argument('--theta13',type=float,default=0.1562,
                        help='''theta13 value [rad]''')
    parser.add_argument('--theta23',type=float,default=0.6745,
                        help='''theta23 value [rad]''')
    parser.add_argument('--deltacp',type=float,default=np.pi,
                        help='''deltaCP value to use [rad]''')
    parser.add_argument('-o', '--outfile', dest='outfile', metavar='FILE', type=str,
                        action='store',default="osc_flux.json",
                        help='file to store the output')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='set verbosity level')
    args = parser.parse_args()

    #Set verbosity level
    set_verbosity(args.verbose)

    ebins = args.flux_file['nue']['ebins']
    czbins = args.flux_file['nue']['czbins']
    
    if not np.alltrue([is_equal_binning(ebins,args.flux_file[nu]['ebins']) for nu in ['nue','nue_bar','numu','numu_bar']]):
        raise Exception('Flux maps have different energy binning!')
    if not np.alltrue([is_equal_binning(czbins,args.flux_file[nu]['czbins']) for nu in ['nue','nue_bar','numu','numu_bar']]):
        raise Exception('Flux maps have different coszen binning!')


    #Initialize an oscillation service
    osc_service = OscillationService(ebins,czbins)

    logging.info("Getting osc prob maps")
    osc_flux_maps = get_osc_flux(args.flux_file,osc_service,args.deltam21,args.deltam31,args.theta12,
                                 args.theta13,args.theta23,args.deltacp)
    
    #Merge the new parameters into the old ones
    osc_flux_maps['params'] = args.flux_file['params']
    osc_flux_maps['params']['deltam21'] = args.deltam21
    osc_flux_maps['params']['deltam31'] = args.deltam31
    osc_flux_maps['params']['theta12'] = args.theta12
    osc_flux_maps['params']['theta13'] = args.theta13
    osc_flux_maps['params']['theta23'] = args.theta23
    osc_flux_maps['params']['deltacp'] = args.deltacp
    
    #Write out
    logging.info("Saving output to: %s",args.outfile)
    to_json(osc_flux_maps, args.outfile)
    
    
