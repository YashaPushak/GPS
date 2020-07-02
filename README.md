# GPS

Golden Parameter Search (GPS) is an automated algorithm congifuration 
procedure. That is, it seeks to optimize the performance (in terms of
running time) of a target algorithm on a set of instances by automatically
finding high-quality values for the parameters of the target algorithm.

GPS is the first automated algorithm configuration procedure to exploit
recent insights into the structural properties of algorithm configuration
landscapes [Pushak & Hoos, 2018]. In particular, GPS assumes that each
parameter of the target algoritm effects a uni-modal response in the 
performance of the algorithm, when modified individually. Furthermore,
GPS assumes that most parameters of the target algorithm do not strongly
interact, thereby allowing GPS to optimize each parameter semi-independetly
in parallel. These two assumptions allow GPS to quickly and efficiently explore
the parameter configuration space. However, if you have reason to believe that
your particular target algorithm contains parameters that strongly violates
either of these two assumptions, then GPS may not be the appropriate 

## A Note on Current GPS Status

This repository is actively being updated to include a new command line
interface for interacting with GPS, along with substantially more documentation
on how to use it. We anticipate completing this work no later than 2020-07-08.

## Installing GPS

 - Create a python2.7 virtual environment
 - Download the latest version of the parameter configuration space parser
from https://github.com/YashaPushak/PCS 
 - While in the main PCS directory, install PCS with 
`pip install .`
or
`python setup.py install --user`.
 - Download the latest version of GPS from https://github.com/YashaPushak/GPS
 - While in the main GPS directory, install GPS's other required python 
packages
`pip install -r requirements.txt`.
 - Setup a redis database.

## Using GPS

GPS is implemented in python2.7, but is designed to be used from the command
line. To use GPS you will need to launch a master process and one or more
worker processes. The master process will loop through each parameter, check
for newly completely target algorithm runs and queue new target algorithm
runs to be performed. The worker processes will repeatedly check for new
target algorithms, perform them and then save the reuslts. Communication 
between the master and worker processes is done through a redis database.

We have provided an example scenario with an artificial algorithm that 
hallucinates running times. It first determines the difficulty of a given
instance by randomly sampling from a normal distribution, which it uses
as the mean of an exponential distribution, from which is samples a running
time for a particular run of the target algorithm on that instance. This 
running time base is then multiplied together with the output from a simple
function of three independent parameters. This was designed to be an easy
benchmark for GPS that can be run in less than 5 minutes with 2 processors.

To run the scenario, first ensure that you have completed all the installation
instructions (including updating the redis_configuration.txt file to point GPS
to the redis database). Then, from the base GPS directory you should run

    python2 run_gps_master.py --experiment-dir examples/artificial-algorithm/ --scenario-file scenario.txt --redis-dbid 0

This will setup the scenario files and output directory for the GPS run. It will
then stop and wait until there is at least 1 GPS worker ready to start. Next,
in a second terminal, run 

    python2 run_gps_worker.py --redis-dbid 0

Note that you do not need to set any arguments other than the redis database
ID. The first process you started will have already created all of the files
necessary for the GPS run, including a new copy of the scenario file with all
GPS arguments fully instantiated. The worker will connect to the specified 
database to determine the location of these files, and then it will begin to
query the database for target algorithm runs to perform. At this time, the
original process will begin running the GPS master process. 

The entire process should take less than 5 minutes to run (often 1-3 on our 
machines). See examples/artificial-algorithm/readme.txt for more details on
the scenario and the expected output from GPS.

### Target Algorithm Wrapper

When performing automated algorithm configuration, it is typical to use a
target algorithm wrapper that implements a particular interface between
the algorithm configurator and the target algorithm. The target algorithm
wrapper should be callable via a command line with a pre-defined argument
format, and should output to the console the reuslt from the run, again
using a predefined syntax for the response. The target algorithm wrapper
is responsable for calling the target algorithm using the specified
configuration on the specified instance, measuring the runing time or
solution quality, and enforcing the running time cutoff. GPS uses the same
interface as SMAC and ParamILS, which means that you can directly use any
scenarios set up for use with the generic wrapper for algorithm 
configuration available from https://github.com/automl/GenericWrapper4AC.

The format for the wrapper command line calls must conform to the following:

    wrapper_name instance_name instance_specifics running_time_cutoff run_length seed -a_parameter_name 'a_parameter_value' -another_parameter_name 'another_parameter_value' ...

Currently, GPS does not support the instance-specific information or the
run-length arguments. GPS will pass values 0 for both of these.

The wrapper may output any amount of information to the command line. However,
each call to the wrapper should produce exactly one line of output in the
following format:

   Result for GPS: run_status, runtime, solution_quality, miscellaneous_data

GPS will also accept `Result for SMAC:` and `Result for ParamILS:` as the
beginning of the line. 

The `run_status` must be one of: `SUCCESS`, `CRASHED`
or `TIMEOUT`. For historical reason, GPS will also treat `SAT` and `UNSAT` as
`SUCCESS`, anything else will be treated as `CRASHED`.

The `runtime` should be the running time spent by your target algorithm. This
is the value that GPS uses as it's objective function. This is also the number
used by GPS to update the CPU time spent on its CPU time configuration budget.
If the run result is either `TIMEOUT` or `CRASHED`, GPS will still use this
running time to appropriately update the time spent in the budget, but will 
otherwise ignore the running time value, since it will penalize the 
configuration in question for being unable to produce correct output (within
the running time cutoff limit). 

At this time, GPS does not support solution quality optimization and will 
ignore the `solution_quality` field. 

The `miscellaneous_data` field can contain any additional details about the 
target algorithm run that you choose. GPS parses it as a string, but otherwise
ignores this information. For backwards compatibility with other configurators,
this field should not contain any commas.

### Instance File Format

## Contact

Yasha Pushak  
ypushak@cs.ubc.ca  

PhD Student & Vanier Scholar  
Department of Computer Science  
The University of British Columbia  
