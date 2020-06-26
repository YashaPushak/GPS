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

To run the scenario, from the base GPS directory you should run

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

## Contact

Yasha Pushak  
ypushak@cs.ubc.ca  

PhD Student & Vanier Scholar  
Department of Computer Science  
The University of British Columbia  
