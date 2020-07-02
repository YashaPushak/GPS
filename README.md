# Golden Parameter Search (GPS)

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
either of these two assumptions, then GPS may not be the appropriate algorithm
configuration procedure for you. 

# A Note on Current GPS Status

This repository is actively being updated to include a new command line
interface for interacting with GPS, along with substantially more documentation
on how to use it. We anticipate completing this work no later than 2020-07-08.

# Table of Contents

   * [Golden Parameter Search GPS](#golden-parameter-search-gps)
   * [A Note on Current GPS Status](#a-note-on-current-gps-status)
   * [Table of Contents](#table-of-contents)
   * [Installing GPS](#installing-gps)
   * [Using GPS](#using-gps)
      * [Target Algorithm Wrapper](#target-algorithm-wrapper)
         * [Target Algorithm Wrapper Input](#target-algorithm-wrapper-input)
         * [Target Algorithm Wrapper Output](#target-algorithm-wrapper-output)
      * [Instance File Format](#instance-file-format)
      * [Parameter Configuration Space File Format](#parameter-configuration-space-file-format)
         * [Conditional Parameters](#conditional-parameters)
         * [Forbidden Statements](#forbidden-statements)
         * [Old Parameter Configuration Space Syntax](#old-parameter-configuration-space-syntax)
   * [Contact](#contact)

# Installing GPS

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

# Using GPS

GPS is implemented in python2.7, but is designed to be used from the command
line. To use GPS you will need to launch a master process and one or more
worker processes. The master process will loop through each parameter, check
for newly completely target algorithm runs and queue new target algorithm
runs to be performed. The worker processes will repeatedly check for new
target algorithms, perform them and then save the reuslts. Communication 
between the master and worker processes is done through a redis database.

## Quick Start Guide

To use GPS, you must provide it with several minimum requirements. We will
use the artificial algorithm example scenario provided with GPS as a running
example. This artificial algorithm hallucinates running times for simulated
parameter responses, all of which is designed to approximate the behaviour
of real target algorithms. The scenario was designed to be an easy benchmark 
for GPS that can be run in less than 5 minutes with 2 processors (it typically
takes between 60-90 seconds on our machines).

GPS requires several pieces of information about your scenario to run:
 
*Target Algorithm:* A target algorithm to optimize callable via the command 
line. This corresponds to the GPS's `algo` argument. For example: 
`--algo 'python2 examples/artificial-algorithm/algorithm.py'`.
See [Target Algorithm Wrapper]#(target-algorithm-wrapper) for more 
details.

*Instance File:* A file that specifies the instances on which your your target
algorithm should be evaluated. Each line should contain a single instance name.
This corresponds to the `instance-file` parameter. For example:
`--instance-file examples/artificial-algorithm/instances.txt`
See [Instance File Format]#(instance-file-format) for more details.

*Parameter Configuration Space File:* A parameter configuration space (.pcs) file, which defines the parameters
of your target algorithm that GPS should optimize, including their names,
(suggested) domains and default values. This corresponds to the `pcs-file`
argument. For example:
`--pcs-file examples/artificial-algorithm/params.pcs`
See [Parameter Configuration Space File Format]#(parameter-configuration-space-file-format)
for more details.

*Configuration Budget:* You must specify a configuration budget using at 
least one of GPS's three configuration budget limits. These are:
 - `wallclock-limit` - Which specifies the total wall clock time allowed
for the GPS run.
 - `cputime-limit` - Which specifies the total amount of CPU time allowed
to be spent evaluating configurations (exlcuding overhead from GPS) for
the GPS run.
 - `runcount-limit` - Which specifies the total number of target algorithm
runs allowed for the GPS run.
You may use multiple configuration budget limits together. For example:
`--runcount-limit 400 --cputime-limit 14400`. Whichever one is exhausted
first will terminate the GPS run. 

*Redis Database Configuration:* You must also tell GPS how to connect to
your redis database server. Normally, you will want to specify both the 
redis host and port using the `redis_configuration.txt` file in the main
GPS directory, as these will typically not change between GPS runs. For
example, the file contents could be:
    redis-host = localhost
    redis-port = 9503
If you choose, you can also specify this information on the command line:
`--redis-host localhost --redis-port 9503`.

You will also need to speciy the redis database instance ID to be used
for the GPS run. You can perform multiple independent runs of GPS in
parallel, in which case each run must use a separate database ID. For
this reason, we recommend to always specify this value on the command line.
For example:
`--redis-dbid 0`.

### Example command line call for GPS

Combining all of the above examples, you're now ready to perform your first
run of GPS. From the base GPS directory, run:

    python2 run_gps_master.py --algo 'python2 examples/artificial-algorithm/algorithm.py' --instance_file examples/artificial-algorithm/instances.txt --pcs-file examples/artificial-algorithm/params.pcs --runcount-limit 400 --cputime-limit 14400 --redis-dbid 0

This will setup the scenario files and output directory for the GPS run. It will
then stop and wait until there is at least 1 GPS worker ready to start. It should
print similar output to the following to the console:

    [INFO]:2020-07-02 11:39:05,801: Starting new GPS run with GPS ID 4RP76T
    [INFO]:2020-07-02 11:39:05,804: Waiting until all workers are ready...
    [INFO]:2020-07-02 11:39:06,806: There are 0 out of a minimum of 1 workers ready...

Next, in a second terminal, run 

    python2 run_gps_worker.py --redis-dbid 0

Note that you do not need to set any arguments other than the redis database
ID. The first process you started will have already created all of the files
necessary for the GPS run, including a new copy of the scenario file with all
GPS arguments fully instantiated. The worker will connect to the specified 
database to determine the location of these files, and then it will begin to
query the database for target algorithm runs to perform. At this time, the
original process will begin running the GPS master process. (Note, you can
also start the worker process before the master process if you choose.)

The entire process should take less than 5 minutes to run (often 1-3 on our 
machines). See examples/artificial-algorithm/readme.txt for more details on
the scenario and the expected output from GPS. While running, GPS will print
information to the console on the current status of its run, including any
time it updates the value of a parameter in the incumbent configuration. 
When it is done, you should see output similar to the following printed to 
the console from the master process:

    [INFO]:2020-07-02 11:40:34,070: Reason for stopping: run budget exhausted
    [INFO]:2020-07-02 11:40:34,070: Used: 10289.0807883 CPU Seconds on target algorithm runs
    [INFO]:2020-07-02 11:40:34,071: Used: 67.2261619568 Wall Clock Seconds (total)
    [INFO]:2020-07-02 11:40:34,071: Used: 400 target algorithm runs.
    [INFO]:2020-07-02 11:40:34,071: Final Incumbent:  -heuristic 'a' -x0 '5' -x1 '0.999546896146'

However, since GPS is a randomized algorithm the exact output will vary.

The worker process

### Using a Scenario file

    python2 run_gps_master.py --experiment-dir examples/artificial-algorithm/ --scenario-file scenario.txt --redis-dbid 0

## Target Algorithm Wrapper

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

### Target Algorithm Wrapper Input

The format for the wrapper command line calls must conform to the following:

    wrapper_name instance_name instance_specifics running_time_cutoff run_length seed -a_parameter_name 'a_parameter_value' -another_parameter_name 'another_parameter_value' ...

The `wrapper_name` will correspond to the value you specify for GPS's `algo`
argument. 

The `instance_name` will correspond to one of the lines from your problem
instance file (see below).

The `running_time_cutoff` will be a positive real number. Your target algorithm
should respect this running time cutoff as closely as possible.

Currently, GPS does not support the instance-specific information or the
run-length arguments. GPS will pass values 0 for both of these.

The remaining parameters passed will specify the configuration to be evaluated.
Parameter names will be preceeded with a single dash. Following the parameter
name there will be a single space and then the value for the parameter in 
single quotes. If you specify any conditional, parent-child relationships 
between your parameters, GPS will automatically remove any disabled children
parameters prior to passing the configuration to your wrapper.

### Target Algorithm Wrapper Output

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
is the value that GPS uses as its objective function. This is also the number
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

## Instance File Format

GPS requires that a text file that specifies the problem instances on which 
your target algorithm should be evaluated. Each line specifies the name of an
instance, with one line per instance. It is common for instances to correspond
to filenames; however, GPS treats them only as strings, so you may specify
any kind of information as needed for your scenario, provided that it does not
contain any spaces. 

At this time, GPS does not support instance-specific information.

## Parameter Configuration Space File Format

GPS requires a file that specifies the parameters of your target algorithm
that are to be configured, containing the type of each parameter, the domain of
values to be searched, and their default values.

GPS supports a subset of the parameter configuration space (.pcs) file formats 
used by SMAC and ParamILS. In short, it supports most of the old and new 
syntax, but it does not support forbidden statements or advanced conditional 
statements. 

Each line in the parameter configuration space file should either specify a 
single parameter, should be a comment (beggining with "#") or should be left
blank. The general format is:

    parameter_name parameter_type parameter_range default_value [log] # Comment

The `parameter_name` should not contain any spaces. 

The `parameter_type` should be one of: `real`, `integer` or `categorical`. 
Ordinal parameters are not currently supported by GPS, and should be encoded as
integer-valued parameters.

If the `parameter_type` is `real` or `integer`, then the `parameter_range` 
should be specified in the following format: `[lower_bound, upper_bound]`.
Note that unlike other algorithm configurators (e.g., SMAC or ParamILS),
GPS does not treat these bounds as strict upper and lower limits, but instead
as guidelines indicating promising regions of the configuration space. This
means that if GPS sees evidence that values outside of this range will improve
the performance of your target algorithm it will not hesitate to attempt them.
If values outside of this range do not produce valid confiugrations
(for example, the parameter specifies a probability), then it is up to you to 
monitor for these values. You can handle this case in any way that you deem 
appropriate, for example, but raising an exception (and returning a `CRASH` 
result to GPS), or by saturating the parameter value at the minimum or maximum.
If desired, you can implement this in your target algorithm wrapper instead of 
your algorithm. 

If the `parameter_type` is `categorical`, then the `parameter_range` should be
specified in the following format: `{value_1, value_2, ..., value_n}`. Where 
each value is a space-free string that specifies one of the possible values for
the parameter.

The `default_value` for your parameter should be contained within square
brackets, and should be within the domain of values specified.

You may optionally append the word `log` (without square brackets) at the end
of a line to suggest the parameter should be searched on a log scale.
Currently this option is ignored by GPS.

You may also optionally append a `#` followed by any text to the end of any
line, will GPS will treat this as a comment and ingore it.

### Conditional Parameters

GPS also accepts conditional parameters, which may be specified using the
following syntax:

    child_parameter_name | parent_parameter_name == parent_parameter_value # comment

GPS does not support other operators, for example `in` or `>`. If you need to 
support this behaviour, you must create one child parameter for each value of
the parameter parameter that should enable the child. 

### Forbidden Statements

GPS does not currently support forbidden statements. If there are combinations 
of parameter values that do not yield valid confiugraitons, then you can
instead detect these configurations in your wrapper and return a `CRASHED` run
status without bothering to call your target algorithm. However, if your
forbidden statements are complex, then you may wish to choose a different 
algorithm configurator (e.g., SMAC), since GPS assumes that your target 
algorithm parameters do not interact strongly, and hence this could cause
performance degradation for GPS.

### Old Parameter Configuration Space Syntax

GPS also supports the old parameter configuration space syntax. For example:

    parameter_name [lower_bound, upper_bound] [default] i # for an integer-valued parameter
    parameter_name [lower_bound, upper_bound] [default # for a real-valued parameter
    parameter_name {value_1, value_2, ..., value_n} [default] # for a categorical parameter

# Contact

Yasha Pushak  
ypushak@cs.ubc.ca  

PhD Student & Vanier Scholar  
Department of Computer Science  
The University of British Columbia  
