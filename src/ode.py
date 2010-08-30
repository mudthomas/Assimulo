#!/usr/bin/env python 
# -*- coding: utf-8 -*-

# Copyright (C) 2010 Modelon AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy as N
import pylab as P
import scipy as S
import scipy.linalg as LIN
import time

class ODE_Exception(Exception):
    """ An integrator exception. """
    pass

class ODE(object):
    """
    Base class for all our integrators.
    """
    
    def __init__(self):
        """
        Defines general starting attributes for a simulation
        problem.
        """
        
        #Default values
        try:
            #Test if the solver is being reinitiated and if so, keep the settings.
            self.verbosity
        except AttributeError:
            #Default values
            self.verbosity = self.NORMAL #Output level
            self.maxsteps = 10000 #Max number of steps
            self.atol = 1.0e-6 #Absolute tolerance
            self.rtol = 1.0e-6 #Relative tolerance
            self.store_cont = False #No continuous logging
            self.sim_complete = False #Simulation finished? Used for time-events
            
            #Internal values
            self._completed_step = False #Completed step option.
            self._time_function  = False #Time event function specified.
        
        #Internal values
        self._SAFETY = 100*N.finfo('double').eps
        self._log_event_info = []
        self._flag_init = True
    
    def _set_max_steps(self, maxsteps):
        """
        Determines the maximum number of steps the solver is allowed
        to take to finish the simulation.
        
            Parameters::
            
                maxsteps    
                            - Default '10000'.
                            
                            - Should be an integer.
                            
                                Example:
                                    maxsteps = 1000.
                                    
        """
        if not isinstance(maxsteps,int):
            raise ODE_Exception('The maximum number of steps must be an integer.')
        if maxsteps < 1:
            raise ODE_Exception('The maximum number of steps must be a positive integer.')
        self.__max_steps = maxsteps
    
    def _get_max_steps(self):
        """
        Determines the maximum number of steps the solver is allowed
        to take to finish the simulation.
        
            Parameters::
            
                maxsteps    
                            - Default '10000'.
                            
                            - Should be an integer.
                            
                                Example:
                                    maxsteps = 1000.
                                    
        """
        return self.__max_steps

    maxsteps = property(_get_max_steps, _set_max_steps)
    

    def _set_problem_name(self, name):
        """
        Defines the name of the problem. Which is then used
        in the plots and when printing the result.
        
            Parameters::
            
                problem_name    
                            - Name of the problem.
                        
                            - Should be a string.
                        
                                Example:
                                    problem_name = 'My Problem'

        """
        self.__name = name
        
    def _get_problem_name(self):
        """
        Defines the name of the problem. Which is then used
        in the plots and when printing the result.
        
            Parameters::
            
                problem_name   
                            - Name of the problem.
                        
                            - Should be a string.
                        
                                Example:
                                    problem_name = 'My Problem'

        """
        return self.__name
        
    problem_name = property(_get_problem_name, _set_problem_name)
    
    @property
    def is_disc(self):
        """Method to test if we are at an event."""
        return False
        
    def simulation_complete(self):
        """
        Method which returns a boolean value determining if the
        simulation completed to tfinal. Used for determining 
        time-events.
        
            Returns::
            
                sim_complete
                            - Boolean value
                                -True for success
                                -False for not complete
        """
        #return self.sim_complete
        return True
    
    #Verbosity levels
    QUIET = 0
    WHISPER = 1
    NORMAL = 2
    LOUD = 3
    SCREAM = 4
    VERBOSE_VALUES = [QUIET, WHISPER, NORMAL, LOUD, SCREAM]
    def _get_verbosity(self):
        """
        Defines the verbosity of the integrator. The verbosity levels are used to
        determine the amount of output from the integrater the user wishes to receive.
        
            Parameters::
            
                verbosity   
                            - Default 'NORMAL'. Can be set to either,
                                
                                - QUIET = 0
                                - WHISPER = 1
                                - NORMAL = 2
                                - LOUD = 3
                                - SCREAM = 4
                            
                            - Should be an integer.
                            
                                Example:
                                    verbosity = 3

            
        """
        return self.__verbosity
        
    def _set_verbosity(self, verbosity):
        """
        Defines the verbosity of the integrator. The verbosity levels are used to
        determine the amount of output from the integrater the user wishes to receive.
        
            Parameters::
            
                    verbosity   
                            - Default 'NORMAL'. Can be set to either,
                                
                                - QUIET = 0
                                - WHISPER = 1
                                - NORMAL = 2
                                - LOUD = 3
                                - SCREAM = 4
                            
                            - Should be an integer.
                            
                                Example:
                                    verbosity = 3

            
        """
        if verbosity not in self.VERBOSE_VALUES:
            raise ODE_Exception('Verbosity values must be within %s - %s'%(self.QUIET, self.SCREAM))
        self.__verbosity = verbosity
        
    verbosity = property(_get_verbosity, _set_verbosity)
    
    def print_verbos(self,list,minimal_verbosity_level):
        """
        Conditional message printing.
        The items in list are printed if the desired verbosity level is greater or equal 
        the minimal verbosity level for this message.
        
        Parameters::
        
            list                               list opr tuple of items to be printed
            minimal_verbosity_level            integer in range 0 (Quiet) to 4 (Scream)
            
        Depends on the attribute self.verbosity
        """ 
        if self.verbosity not in self.VERBOSE_VALUES:
            raise ODE_Exception('Verbosity values must be within %s - %s'%(self.QUIET, self.SCREAM))    
        if self.verbosity >= minimal_verbosity_level:
            for expr in list:
                print expr
    
    def simulate(self,tfinal, ncp=0):
        """
        Calls the integrator to perform the simulation over the given time-interval. 
        If a second call to simulate is performed, the simulation starts from the last
        given final time.
        
            Parameters::
            
                tfinal  
                        - Final time for the simulation
                
                        - Should be a float or integer greater than the initial time.
                        
                ncp     
                        - Default '0'. Number of communication points where the 
                          solution is returned. If '0', the integrator will return 
                          at its internal steps.
                          
                        - Should be an integer.
                          
                    Example:
                    
                        __call__(10.0, 100), 10.0 is the final time and 100 is the number
                                             communication points.
                 
        """
        self.__call__(tfinal,ncp)
    
    def initiate(self):
        """
        Initiates the problem (if defined in the problem class).
        """
        self._problem.initiate(self)
    
    def print_event_info(self):
        """
        Prints the event information.
        """
        for i in range(len(self._log_event_info)):
            print 'Time, t = %e'%self._log_event_info[i][0]
            print '  Event info, ', self._log_event_info[i][1]
        print 'Number of events: ', len(self._log_event_info)
    
    def print_statistics(self):
        """
        Should print the statistics.
        """
        pass
    
    def _get_store_cont(self):
        """
        Defines how the method handle_result is called. For more information
        see the help text under handle_result in either Implicit_Problem or
        Explicit_Problem .
        
            Parameters::
            
                post_process
                        - Default 'False'.
                        
                        - Should be convertable to boolean.
                        
                            Example:
                                store_cont = True
        """
        return self.__storecont
    def _set_store_cont(self, cont):
        """
        Defines how the method handle_result is called. For more information
        see the help text under handle_result in either Implicit_Problem or
        Explicit_Problem .
        
            Parameters::
            
                post_process
                        - Default 'False'.
                        
                        - Should be convertable to boolean.
                        
                            Example:
                                store_cont = True
        """
        self.__storecont = bool(cont)
        
    store_cont = property(_get_store_cont, _set_store_cont)
    