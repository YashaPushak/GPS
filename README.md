# Golden Parameter Search (GPS)

Golden Parameter Search (GPS) [Pushak & Hoos, 2020] is an automated 
algorithm congifuration procedure. That is, it seeks to optimize the 
performance of a target algorithm on a set of instances by automatically 
finding high-quality values for the parameters of the target algorithm. GPS 
can optimze the performance of an algorithm in terms of either the running
time required to solve problem instances or the solution quality found by
the target algorithm for the problem instances.
 
GPS is the first automated algorithm configuration procedure to exploit
recent insights into the structural properties of algorithm configuration
landscapes [Pushak & Hoos, 2018]. In particular, GPS assumes that each
parameter of the target algoritm effects a uni-modal response in the 
performance of the algorithm, when modified individually. Furthermore,
GPS assumes that most parameters of the target algorithm do not strongly
interact, thereby allowing GPS to optimize each parameter semi-independently
in parallel. These two assumptions allow GPS to quickly and efficiently explore
the parameter configuration space. However, if you have reason to believe that
your particular target algorithm contains parameters that strongly violates
either of these two assumptions, then GPS may not be the appropriate algorithm
configuration procedure for you. 

If you use GPS in your work, please consider citing our paper.

 - Yasha Pushak and Holger H. Hoos.  
**Golden Parameter Search: Exploiting Structure to Quickly Configure Parameters
In Parallel.**  
*In Proceedings of the Twenty-Second Interntional Genetic and Evolutionary 
Computation Conference (GECCO 2020)*. pp 245-253 (2020).  
**Won the 2020 GECCO ECOM Track best paper award.**
 - Yasha Pushak and Holger H. Hoos.  
**Algorithm Configuration Landscapes: More Benign than Expected?**  
*In Proceedings of the Fifteenth Internationl Conference on Parallel Problem 
Solving from Nature (PPSN 2018)*. pp 271-283 (2018).  
**Won the 2018 PPSN best paper award.**

# Table of Contents


   * [Golden Parameter Search (GPS)](#golden-parameter-search-gps)
   * [Table of Contents](#table-of-contents)
   * [Installing GPS](#installing-gps)
      * [Setting up a Redis Database](#setting-up-a-redis-database)
   * [Quick Start Guide](#quick-start-guide)
      * [Required Input](#required-input)
      * [Example command line call for GPS](#example-command-line-call-for-gps)
      * [Experiment Directory](#experiment-directory)
      * [Using a Scenario file](#using-a-scenario-file)
      * [Temporary File Directory - <strong>Important</strong>](#temporary-file-directory---important)
      * [Solution Quality Optimization](#solution-quality-optimization)
   * [Target Algorithm Wrapper](#target-algorithm-wrapper)
      * [Target Algorithm Wrapper Input](#target-algorithm-wrapper-input)
      * [Target Algorithm Wrapper Output](#target-algorithm-wrapper-output)
   * [Instance File Format](#instance-file-format)
   * [Parameter Configuration Space File Format](#parameter-configuration-space-file-format)
      * [Conditional Parameters](#conditional-parameters)
      * [Example Configuration Space](#example-configuration-space)
      * [Forbidden Statements](#forbidden-statements)
      * [Old Parameter Configuration Space Syntax](#old-parameter-configuration-space-syntax)
   * [GPS Arguments](#gps-arguments)
      * [Setup Arguments](#setup-arguments)
      * [Redis Arguments](#redis-arguments)
      * [Scenario Arguments](#scenario-arguments)
      * [GPS Parameters](#gps-parameters)
      * [Post-Process Parameters](#post-process-parameters)
   * [Contact](#contact)

# Installing GPS

 1. Create a python2.7 virtual environment
 2. Download the latest version of the parameter configuration space parser
from https://github.com/YashaPushak/PCS 
 3. While in the main PCS directory, install PCS with 
`pip install .`
or
`python setup.py install --user`.
 4. Download the latest version of GPS from https://github.com/YashaPushak/GPS
 5. While in the main GPS directory, install GPS's other required python 
packages
`pip install -r requirements.txt`.
 6. While in the main GPS directory, install GPS with 
`pip install .`
or 
`python setup.py install --user`
 7. Setup and install a [redis database](#setting-up-a-redis-database). 

## Setting up a Redis Database

These instructions help you to setup a simple local database.
You can find more information on redis on their official website: [redis.io](https://redis.io).
The configuration file provided is only a light modification of [the one provided with redis 5.0](https://raw.githubusercontent.com/antirez/redis/5.0/redis.conf).

You first need to install redis. It is available on most systems, as well as on Anaconda using:

    conda install redis 

To start local a server, use the following command:

    redis-server ./redis/redis.conf

This will start a server that listens to port 9503 on your local machine. It has 16 databases with `dbid` from 0 to 15.

In the file `redis_configuration.txt` change `redis-host` to `localhost`

You should now be ready to run GPS.

# Quick Start Guide

GPS is implemented in python2.7, but is designed to be used from the command
line. To use GPS you will need to launch a master process and one or more
worker processes. The master process will loop through each parameter, check
for newly completely target algorithm runs and queue new target algorithm
runs to be performed. The worker processes will repeatedly check for new
target algorithms, perform them and then save the reuslts. Communication 
between the master and worker processes is done through a redis database.

## Required Input

To use GPS, you must provide it with several minimum requirements. We will
use the artificial algorithm example scenario provided with GPS as a running
example. This artificial algorithm hallucinates running times for simulated
parameter responses, all of which is designed to approximate the behaviour
of real target algorithms. The scenario was designed to be an easy benchmark 
for GPS that can be run in less than 5 minutes with 2 processors (it typically
takes between 60-90 seconds on our machines).

GPS requires several pieces of information about your scenario to run:
 
**Target Algorithm:** A target algorithm to optimize. This corresponds to the
GPS's `algo` argument. For example: 
`--algo 'python2 examples/artificial-algorithm/algorithm.py'`. The target
algorithm can either be callable via the command line, or it can implement
a simple python interface.
See [Target Algorithm Wrapper](#target-algorithm-wrapper) for more details.

**Instance File:** A file that specifies the instances on which your your target
algorithm should be evaluated. Each line should contain a single instance name.
This corresponds to the `instance-file` argument. For example:
`--instance-file examples/artificial-algorithm/instances.txt`
See [Instance File Format](#instance-file-format) for more details.

**Parameter Configuration Space File:** A parameter configuration space (.pcs) 
file, which defines the parameters of your target algorithm that GPS should 
optimize, including their names, (suggested) domains and default values. This 
corresponds to the `pcs-file` argument. For example:
`--pcs-file examples/artificial-algorithm/params.pcs`
See [Parameter Configuration Space File Format](#parameter-configuration-space-file-format)
for more details.

**Target Algorithm Running Time Cutoff:** The maximum amount of time GPS should
wait for a single target algorithm call to complete. Ideally, the default
configuration of your target algorithm should be able to solve at least 90%
of the problem instances within this running time cutoff. The performance of
all algorithm configurators is very sensitive to this parameter. If you are
unsure what value to use, you can use a very large one. GPS will adaptively
limit the running times of the target algorithm calls; however, it may 
initially waste considerable time if some of the first few target algorithm
calls it performs take extremely long to run, since it won't yet know what
a good value to use is. This corresponds to the `algo-cutoff-time` argument
and should be specified in seconds.
For example:
`--algo-cutoff-time 600`

**Configuration Budget:** You must specify a configuration budget using at 
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

**Redis Database Configuration:** You must also tell GPS how to connect to
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

## Example command line call for GPS

Combining all of the above examples, you're now ready to perform your first
run of GPS. From the base GPS directory, run:

    python2 run_gps_master.py --algo 'python2 examples/artificial-algorithm/algorithm.py' --instance_file examples/artificial-algorithm/instances.txt --pcs-file examples/artificial-algorithm/params.pcs --algo-cutoff-time 600 --runcount-limit 400 --cputime-limit 14400 --redis-dbid 0

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
original process will begin running the GPS master process. 

Normally, you would typically want to provide GPS with additional workers to
distribute the work of performing target algorithm runs. There is no limit
to the number of workers that GPS can use. You can continue to start as
many worker processes as you like. However, since this scenario uses an 
artificial algorithm that requires virtually no time to perform the target
algorithm runs, there is no benefit to doing so.

The entire process should take about 60-90 seconds to run, although it 
occassionaly requires up to 5 minutes. While running, GPS will print
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
See `examples/artificial-algorithm/readme.txt` for more information about
this scenario.

## Experiment Directory

Rather than running everything from the GPS root directory, it is often more
convenient to specify the location from which the experiment should be run 
using the `experiment-dir` argument. When this is done, all other relative file 
and directory paths should be specified relative to this directory. Note that
GPS will then change to this directory prior to beginning to run, which means
that any relative paths used internally by your target algorithm or wrapper 
must be available from your experiment directory.

This is also a convenient way to help organize the several output files used
by GPS, as they will be stored in this experiment directory rather than the
directory from which you called GPS. To continue our running example, you
would start the master process with the following command line call:

    python2 run_gps_master.py --experiment-dir examples/artificial-algorithm/ --algo 'python2 algorithm.py' --instance_file instances.txt --pcs-file params.pcs --algo-cutoff-time 600 --runcount-limit 400 --cputime-limit 14400 --redis-dbid 0

The call for the worker process remains the same.

## Using a Scenario file

Rather than using a long command line call to start GPS, it is often helpful
to specify most of GPS's arguments in a scenario file, and then to simply
point GPS to the scenario file. For example, we include the file
`examples/artificial-algorithm/scenario.txt`, which contains the following
argument specifications:

    pcs-file = params.pcs
    algo = python algorithm.py
    algo_cutoff_time = 600
    instances = instances.txt
    # Whichever budget limit is reached first will terminate GPS
    runcount_limit = 400
    # Note that GPS only counts the times reported by your target algorithm in this limit
    # So even though we are giving it 4 hours (14400 seconds), it should actually terminate
    # in around 1-3 minutess, since our artificial algorithm actually spends far less time
    # than it returns
    cputime_limit = 14400
    verbose = 1

Any line that begins with `#` is treated as a comment and ignored. 

You can then start the GPS master process using:

    python2 run_gps_master.py --experiment-dir examples/artificial-algorithm --scenario-file scenario.txt --redis-dbid 0

The call for the worker process remains the same.

Any argument that can be specified on the command line can also be specified 
in a scenario file (except the scenario file itself). If the same argument is
defined multiple times, the order of precedence will be:
command line > scenario file > redis configuration file > GPS default values.

## Temporary File Directory - **Important**

GPS (like other algorithm configurators) creates a large number of temporary 
files that it uses to interact with your target algorithm wrapper (provided
you use the command line interface instead of the python interface). This can
sometimes cause temporary performance degredation for your entire filesystem
(which in turn, can of course impact the quality of the configurations found
by GPS). GPS will clean up these files when it is done with them. However, 
for file systems that automatically back-up files, GPS and other algorithm
configurators can still cause performance degradation. 

For this reason, it 
is **strongly** recommended to provide GPS with the location of a temporary
directory where it can create these files without effecting the performance
of the main filesystem. This directory should not be backed up, and should
ideally be fast to write to.

The temporary directory can be specified using the `temp-dir` argument. For
example: `--temp-dir /tmp`.

GPS does not share temporary files between
processes. So if worker processes are operating on separate nodes of a 
cluster, it is unproblematic for each worker to have access to separate
temporary file directories. 

## Solution Quality Optimization

In addition to minimizing the running times of a target algorithm, GPS can be
used to minimize the solution qualities found by the target algorithm, if 
applicable. For example, used this way GPS can optimize the validation error
of machine learning models through hyper-parameter optimization, or GPS can
be applied to optimize the performance of optimization algorithms, allowing
them to find better solutions within a fixed computational budget. Recent
evidence suggests that for scenarios where both metrics are available, 
optimizing for solution quality should provide configurators with a more
informative objective function, allowing them to find higher-quality
parameter configurations (see, *e.g.*, Hall *et al.*, 2020, "Analysis of the 
Performance of Algorithm Configurators for Search Heuristics with Global 
Mutation Operators").

An example artificial scenario showing how to use GPS for solution quality
optimization can be found in `./examples/artificial-classifier`,
which is designed to approximately resemble the behaviour of a machine learning
binary classification scenario. This scenario can be run with:

    python run_gps_master.py --experiment-dir examples/artificial-classifier --scenario-file scenario.txt --dbid 0

and

    python run_gps_worker.py --dbid 0

Apart from providing GPS with the solution quality to optimize, it 
is required to specify in the scenario file that the `run_obj` is `QUALITY`
instead of the default `RUNTIME`. When optimizing solution quality, GPS 
will minimize the mean solution quality.

Note that it does not make sense to use adaptive capping when performing
solution quality optimization. Therefore, adaptive capping will be disabled
and any values passed to the `bound_multiplier` parameter will be ignored. 


# Target Algorithm Wrapper

When performing automated algorithm configuration, it is typical to use a
target algorithm wrapper that implements a particular command line interface
between the algorithm configurator and the target algorithm. GPS supports both
the conventional command line interface, as well as a python interface.
The target algorithm wrapper is responsable for calling the target algorithm 
using the specified configuration on the specified instance, measuring the
runing time or solution quality (*e.g.*, validation loss), and enforcing the 
running time cutoff. 

GPS uses the same command line interface as SMAC and 
ParamILS, which means that you can directly use any scenarios set up for use
with the generic wrapper for algorithm configuration available from 
https://github.com/automl/GenericWrapper4AC. However, if your target algorithm
is implemented in python, then using the python interface will potentially 
speed up configuration process and improve the quality of the configurations 
found. This is because the python interface allows you to load and initialize
data/instances a single time (per worker), and then re-use this data for each
target algorithm call, whereas due to the nature of command line interfaces
you must instead re-load the instances from the disk for every target algorithm
call, which may be costly. The python interface is further advantageous as it
removes the need for GPS to constantly write to and read from temporary files
on the disk.

## Command Line Target Algorithm Wrapper Format

The command line interface require input and output in a pre-defined format.

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

### Python Target Algorithm Wrapper Interface

To use the python interface you will need to create a class called
`TargetAlgorithmRunner` that inherits from GPS's `AbstractRunner`
class and implements two functions: `__init__` and `perform_run`.

The `__init__` function should be used to load and initialize any needed 
instance data. However, you may also choose to do this in a lazy format, by
only loading and saving instance data when it is first needed by `perform_run`.

The `perform_run` function should accept several key-word arguments defining,
for example, the configuration to be evaluated, the instance on which the
configuration will be evaluated, the maximum budget (`cutoff`) to be used by
the target algorithm for this particular run, *etc.*

We provide an example implementation below

    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    
    from GPS.abstract_runner import AbstractRunner

    # Note that the class name must match this exactly!
    class TargetAlgorithmWrapper(AbstractRunner):

        def __init__(self):


# Instance File Format

GPS requires that a text file that specifies the problem instances on which 
your target algorithm should be evaluated. Each line specifies the name of an
instance, with one line per instance. It is common for instances to correspond
to filenames; however, GPS treats them only as strings, so you may specify
any kind of information as needed for your scenario, provided that it does not
contain any spaces. 

At this time, GPS does not support instance-specific information.

# Parameter Configuration Space File Format

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

## Conditional Parameters

GPS also accepts conditional parameters, which may be specified using the
following syntax:

    child_parameter_name | parent_parameter_name == parent_parameter_value # comment

GPS does not support other operators, for example `in` or `>`. If you need to 
support this behaviour, you must create one child parameter for each value of
the parameter parameter that should enable the child (see example below).

Note that GPS can have any number of children for a single parent parameter;
however, GPS can only have a child parameter can only be defined for a single
value of its parent parameter. This does not limit the number of parents
or ancestors that a child can have -- however; each such parent or ancestor
must enable the child for only a single value. This means that if you have
the following:

    param1 | param2 in {a, b}
    param1 | param3 in {a, b}

you will need to encode this as, for example:

    param1_2a_3a | param2 == a
    param1_2a_3a | param3 == a

    param1_2b_3a | param2 == b
    param1_2b_3a | param3 == a

    param1_2a_3b | param2 == a
    param1_2a_3b | param3 == b

    param1_2b_3b | param2 == b
    param1_2b_3b | param3 == b

You should then modify your target algorithm wrapper to include 
`param1_2a_3a`, `param1_2b_3a`, `param1_2a_3b` and `param1_2b_3b` as aliases
for `param1`. (Note that only one of these four aliases will ever be passed
to your target algorithm at once time).

## Example Configuration Space

The following configuration space is an extended version of the one used in the
artificial algorithm example, designed to also illustrate conditional parameters.

    # x0 is an integer-valued parameter. We're suggesting to GPS that it should 
    # search values in the range [0, 20] and indicating that 2 is a good default
    # value.
    x0 integer [0, 20] [2]

    # x1 is a real-valued parameter. We're suggesting to GPS that is should
    # search values in the range [0, 20] and indicating that 3 is a good default
    # value.
    x1 real [0, 20] [3]

    # heuristic is a categorical parameter. It can take on three values: a, b
    # or c, which corresponds to three (fictional) heuristics that the 
    # algorithm could use. We're indicating that c is a good default heuristic.
    heuristic categorical {a, b, c} [c]

    # sample_probability is a real-valued parameter. We're suggesting to
    # GPS that it should search values in the range [0, 1]. Note that GPS might
    # actually try values outside of this range if it sees evidence that they
    # might perform better. However, since this is a probability it probably
    # doesn't make sense for these values outside of [0, 1] to be used. If this
    # causes unexpected behaviour for your target algorithm, you should 
    # validate the parameter values prior to running it. You can simply tell
    # GPS that a configuration with an invalid value crashed. 
    sample_probability real [0, 1] [0.05]

    # This tells GPS that sample_probability is a conditional parameter, that
    # is, that your target algorithm only uses this parameter when heuristic
    # is set to a.
    sample_probability | heuristic == a

    # If your algorithm shares a child value for two or more values of a
    # parent parameter, then you must create one copy of the child parameter
    # for each value of the parent for which the child should be used.
    sample_probability_copy real [0, 1] [0.05]
    sample_probability_copy | heuristic == b

## Forbidden Statements

GPS does not currently support forbidden statements. If there are combinations 
of parameter values that do not yield valid confiugraitons, then you can
instead detect these configurations in your wrapper and return a `CRASHED` run
status without bothering to call your target algorithm. However, if your
forbidden statements are complex, then you may wish to choose a different 
algorithm configurator (e.g., SMAC), since GPS assumes that your target 
algorithm parameters do not interact strongly, and hence this could cause
performance degradation for GPS.

## Old Parameter Configuration Space Syntax

GPS also supports the old parameter configuration space syntax. For example:

    parameter_name [lower_bound, upper_bound] [default] i # for an integer-valued parameter
    parameter_name [lower_bound, upper_bound] [default] # for a real-valued parameter
    parameter_name {value_1, value_2, ..., value_n} [default] # for a categorical parameter

# GPS Arguments

All of the following arguments can be specified on the command line on in a 
scenario file (except the scenario file itself, which must be defined on the 
command line). To specify an argument in a scenario file, simply remove all
leading dashes. For example, to specify the instance file on the command line
you would use:

    python2 run_gps_master.py --instance-file /path/to/instances.txt

To specify the same in the scenario file you would place: 

    instance-file = /path/to/instances.txt

in the scenario file.

**GPS Argument Table of Contents:**

   * [Setup Arguments](#setup-arguments)
      * [experiment_dir](#experiment_dir)
      * [output_dir](#output_dir)
      * [scenario_file](#scenario_file)
      * [temp_dir](#temp_dir)
      * [verbose](#verbose)
   * [Redis Arguments](#redis-arguments)
      * [redis_dbid](#redis_dbid)
      * [redis_host](#redis_host)
      * [redis_port](#redis_port)
   * [Scenario Arguments](#scenario-arguments)
      * [algo](#algo)
      * [algo_cutoff_time](#algo_cutoff_time)
      * [cputime_limit](#cputime_limit)
      * [instance_file](#instance_file)
      * [pcs_file](#pcs_file)
      * [run_obj](#run_obj)
      * [runcount_limit](#runcount_limit)
      * [seed](#seed)
      * [wallclock_limit](#wallclock_limit)
   * [GPS Parameters](#gps-parameters)
      * [alpha](#alpha)
      * [bound_multiplier](#bound_multiplier)
      * [decay_rate](#decay_rate)
      * [instance_increment](#instance_increment)
      * [minimum_runs](#minimum_runs)
      * [minimum_workers](#minimum_workers)
      * [post_process_incumbent](#post_process_incumbent)
      * [share_instance_order](#share_instance_order)
      * [sleep_time](#sleep_time)
   * [Post-Process Parameters](#post-process-parameters)
      * [post_process_alpha](#post_process_alpha)
      * [post_process_min_runs](#post_process_min_runs)
      * [post_process_multiple_test_correction](#post_process_multiple_test_correction)
      * [post_process_n_permutations](#post_process_n_permutations)

## Setup Arguments

These are general GPS arguments that are used to set up the GPS run.

### experiment_dir

<table>
<tr><td><b>Description</b></td><td>The root directory from which experiments will be run. By default, this is the current working directory. GPS will change to this directory prior to running, this means that if relative paths are specified for any other files or directories then they must be given relative to your experiment directory.</td></tr>
<tr><td><b>Default</b></td><td><code>.</code></td></tr>
<tr><td><b>Aliases</b></td><td><code>--experiment-dir</code>, <code>--experiment_dir</code>, <code>--experimentDir</code>, <code>--experimentdir</code>, <code>--exec-dir</code>, <code>--exec_dir</code>, <code>--execDir</code>, <code>--execdir</code>, <code>-e</code></td></tr>
</table>

### output_dir

<table>
<tr><td><b>Description</b></td><td>The directory where output will be stored. The actual directory for a particular GPS run with ID gps_id will be stored in {experiment-dir}/{output-dir}/gps-run-{gps_id}</td></tr>
<tr><td><b>Default</b></td><td><code>gps-output</code></td></tr>
<tr><td><b>Aliases</b></td><td><code>--output-dir</code>, <code>--output_dir</code>, <code>--outputDir</code>, <code>--outputdir</code>, <code>--output-directory</code>, <code>--output_directory</code>, <code>--outputDirectory</code>, <code>--outputdirectory</code>, <code>--out-dir</code>, <code>--out_dir</code>, <code>--outDir</code>, <code>--outdir</code>, <code>--log-location</code>, <code>--log_location</code>, <code>--logLocation</code>, <code>--loglocation</code></td></tr>
</table>

### scenario_file

<table>
<tr><td><b>Description</b></td><td>The scenario file (and location) that defines what settings are used for GPS.</td></tr>
<tr><td><b>Default</b></td><td>None</td></tr>
<tr><td><b>Aliases</b></td><td><code>--scenario-file</code>, <code>--scenario_file</code>, <code>--scenarioFile</code>, <code>--scenariofile</code>, <code>--scenario</code></td></tr>
</table>

### temp_dir

<table>
<tr><td><b>Description</b></td><td>The directory for GPS to use to write temporary files to. By default, GPS will write all temporary files to the current working directory (<i>i.e.</i>, the experiment-dir. GPS will also clean up all such temporary files when it is done with them, unless GPS crashes unexpectedly. GPS will create a single temporary file for every target algorithm run, which means that it will create and delete and large number of these files. It is therefore strongly recommended to use a directory with a fast filesystem that is not automatically backed up. In some cases, GPS and other algorithm configurators with similar behaviour have been known to unneccesarily stress file systems with automatic back-ups due to the volume of temporary files created and deleted. If this happens, the quality of the configurations found with GPS (when using a wall clock budget) may suffer substantially, as well as any other person or system that interacts with the filesystem.</td></tr>
<tr><td><b>Default</b></td><td><code>.</code></td></tr>
<tr><td><b>Aliases</b></td><td><code>--temp-dir</code>, <code>--temp_dir</code>, <code>--tempDir</code>, <code>--tempdir</code>, <code>--temp</code>, <code>--temporary-directory</code>, <code>--temporary_directory</code>, <code>--temporaryDirectory</code>, <code>--temporarydirectory</code></td></tr>
</table>

### verbose

<table>
<tr><td><b>Description</b></td><td>Controls the verbosity of GPS's output. Set of 0 for warnings only. Set to 1 for more informative messages. And set to 2 for debug-level messages. The default is 1.</td></tr>
<tr><td><b>Default</b></td><td>1</td></tr>
<tr><td><b>Aliases</b></td><td><code>--verbose</code>, <code>--verbosity</code>, <code>--log-level</code>, <code>--log_level</code>, <code>--logLevel</code>, <code>--loglevel</code>, <code>-v</code></td></tr>
</table>

## Redis Arguments

These arguments are required to configure GPS so that it connect to your redis server installation, which it uses to communicate between master and worker processes.

### redis_dbid

<table>
<tr><td><b>Description</b></td><td>The redis database ID number to be used by this instance of GPS. All workers of this GPS instance must be given this ID. Each concurrent GPS instance must have a unique database ID.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--redis-dbid</code>, <code>--redis_dbid</code>, <code>--redisDbid</code>, <code>--redisdbid</code>, <code>--dbid</code></td></tr>
</table>

### redis_host

<table>
<tr><td><b>Description</b></td><td>The redis database host name.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--redis-host</code>, <code>--redis_host</code>, <code>--redisHost</code>, <code>--redishost</code>, <code>--host</code></td></tr>
</table>

### redis_port

<table>
<tr><td><b>Description</b></td><td>The redis database port number.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--redis-port</code>, <code>--redis_port</code>, <code>--redisPort</code>, <code>--redisport</code>, <code>--port</code></td></tr>
</table>

## Scenario Arguments

These arguments define the scenario-specific information.

### algo

<table>
<tr><td><b>Description</b></td><td>If algorithm-type is 'COMMAND_LINE', then this should be the command line string used to execute the target algorithm. Otherwise, this should be the name of the python file that implements the target-algorithm interface.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--algo</code>, <code>--algo-exec</code>, <code>--algo_exec</code>, <code>--algoExec</code>, <code>--algoexec</code>, <code>--algorithm</code>, <code>--wrapper</code></td></tr>
</table>

### algo_cutoff_time

<table>
<tr><td><b>Description</b></td><td>The CPU time limit for an individual target algorithm run, in seconds. If adaptive capping is used, GPS may sometimes use smaller cutoff times as well.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--algo-cutoff-time</code>, <code>--algo_cutoff_time</code>, <code>--algoCutoffTime</code>, <code>--algocutofftime</code>, <code>--target-run-cputime-limit</code>, <code>--target_run_cputime_limit</code>, <code>--targetRunCputimeLimit</code>, <code>--targetruncputimelimit</code>, <code>--cutoff-time</code>, <code>--cutoff_time</code>, <code>--cutoffTime</code>, <code>--cutofftime</code>, <code>--cutoff</code></td></tr>
</table>

### algo_type

<table>
<tr><td><b>Description</b></td><td>GPS can interact with your target algorithm either using ACLib's pre-defined command line interface, or more directly by using a python interface. To use the classic command line interface, set to  'COMMAND_LINE', otherwise use 'PYTHON'.</td></tr>
<tr><td><b>Default</b></td><td>COMMAND_LINE</td></tr>
<tr><td><b>Aliases</b></td><td><code>--algo-type</code>, <code>--algo_type</code>, <code>--algoType</code>, <code>--algotype</code>, <code>--algorithm-type</code>, <code>--algorithm_type</code>, <code>--algorithmType</code>, <code>--algorithmtype</code></td></tr>
</table>

### cputime_limit

<table>
<tr><td><b>Description</b></td><td>Limits the total CPU time used by the target algorithm, in seconds. Either this, the runcount or the wallclock limit must be less than the maximum integer value. The default is the maximum integer value. NOTE: Unlike SMAC, this does not include the CPU time spent by GPS -- this only adds the running times reported by your target algorithm wrapper and terminates GPS once they have exceeded this limit.</td></tr>
<tr><td><b>Default</b></td><td>2147483647.0</td></tr>
<tr><td><b>Aliases</b></td><td><code>--cputime-limit</code>, <code>--cputime_limit</code>, <code>--cputimeLimit</code>, <code>--cputimelimit</code>, <code>--tunertime-limit</code>, <code>--tunertime_limit</code>, <code>--tunertimeLimit</code>, <code>--tunertimelimit</code>, <code>--tuner-timeout</code>, <code>--tuner_timeout</code>, <code>--tunerTimeout</code>, <code>--tunertimeout</code></td></tr>
</table>

### instance_file

<table>
<tr><td><b>Description</b></td><td>The file (and location) containing the names of the instances to be used to evaluate the target algorithm's configurations.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--instance-file</code>, <code>--instance_file</code>, <code>--instanceFile</code>, <code>--instancefile</code>, <code>--instances</code>, <code>-i</code></td></tr>
</table>

### pcs_file

<table>
<tr><td><b>Description</b></td><td>The file that contains the algorithm parameter configuration space in PCS format. GPS supports a subset of the syntax used for SMAC and ParamILS.</td></tr>
<tr><td><b>Required</b></td><td>Yes</td></tr>
<tr><td><b>Aliases</b></td><td><code>--pcs-file</code>, <code>--pcs_file</code>, <code>--pcsFile</code>, <code>--pcsfile</code>, <code>--param-file</code>, <code>--param_file</code>, <code>--paramFile</code>, <code>--paramfile</code>, <code>--p</code></td></tr>
</table>

### run_obj

<table>
<tr><td><b>Description</b></td><td>This is the objective that GPS is attempting to minimize. Can be 'RUNTIME' or 'QUALITY' to minimize the target algorithm's running time or solution quality, respectively. If 'RUNTIME', GPS will minimize the PAR10 of the running times.</td></tr>
<tr><td><b>Default</b></td><td>RUNTIME</td></tr>
<tr><td><b>Aliases</b></td><td><code>--run-obj</code>, <code>--run_obj</code>, <code>--runObj</code>, <code>--runobj</code>, <code>--run-objective</code>, <code>--run_objective</code>, <code>--runObjective</code>, <code>--runobjective</code></td></tr>
</table>

### runcount_limit

<table>
<tr><td><b>Description</b></td><td>Limits the total number of target algorithm runs performed by GPS. Either this, the wallclock or CPU time limit must be less than the maximum integer value. The default is the maximum integer value.</td></tr>
<tr><td><b>Default</b></td><td>2147483647</td></tr>
<tr><td><b>Aliases</b></td><td><code>--runcount-limit</code>, <code>--runcount_limit</code>, <code>--runcountLimit</code>, <code>--runcountlimit</code>, <code>--total-num-runs-limit</code>, <code>--total_num_runs_limit</code>, <code>--totalNumRunsLimit</code>, <code>--totalnumrunslimit</code>, <code>--num-runs-limit</code>, <code>--num_runs_limit</code>, <code>--numRunsLimit</code>, <code>--numrunslimit</code>, <code>--number-of-runs-limit</code>, <code>--number_of_runs_limit</code>, <code>--numberOfRunsLimit</code>, <code>--numberofrunslimit</code></td></tr>
</table>

### seed

<table>
<tr><td><b>Description</b></td><td>The random seed used by GPS. If -1, a random value will be used. Note that because GPS is an asychronous parallel algorithm, it is not deterministic even when the seed is set to the same value, as this does not control for random background environmental noise that can affect the running times and order in which GPS receives target algorithm run updates.</td></tr>
<tr><td><b>Default</b></td><td>-1</td></tr>
<tr><td><b>Aliases</b></td><td><code>--seed</code>, <code>-s</code></td></tr>
</table>

### wallclock_limit

<table>
<tr><td><b>Description</b></td><td>Limits the total wall-clock time used by GPS, in seconds. Either this, the runcount  or the CPU time limit must be less than the maximum integer value. The default is the maximum integer value.</td></tr>
<tr><td><b>Default</b></td><td>2147483647.0</td></tr>
<tr><td><b>Aliases</b></td><td><code>--wallclock-limit</code>, <code>--wallclock_limit</code>, <code>--wallclockLimit</code>, <code>--wallclocklimit</code>, <code>--runtime-limit</code>, <code>--runtime_limit</code>, <code>--runtimeLimit</code>, <code>--runtimelimit</code></td></tr>
</table>

## GPS Parameters

These are the parameters of GPS itself. You can use these to modify GPS to best suit your scenario, if desired. Unless you know what you are doing, we recommend not to change these parameters from their defaults, as they have been chosen through careful experimentation. However, we did this manually, so if you have a large enough budget, you could always apply GPS to configure itself, which would no doubt improve the performance of GPS ;) . If you do this, please get in touch! We would love to validate your GPS configuration and include it as the new default settings. 

### alpha

<table>
<tr><td><b>Description</b></td><td>The significance level used in the permutation test to determine whether or not one configuration is better than another. Multiple test correction is not applied, so this is better viewed as a statistically-grounded heuristic than a true significance level. Setting this value too small will slow GPS's progress. Setting this value too high may allow GPS to make mistakes, which could potentially substantially adversely affect the final solution quality of the configurations found; however, it will allow GPS to move through the search space more quickly. If you can only afford to perform a single run of GPS, it is safest to set this parameter on the lower side: perhaps 0.01-0.05. Otherwise, you can experiment with larger values (say 0.1-0.25), which will increase the variance in the output of GPS. This parameter should be in (0,0.25). The default is 0.05.</td></tr>
<tr><td><b>Default</b></td><td>0.05</td></tr>
<tr><td><b>Aliases</b></td><td><code>--alpha</code>, <code>--significance-level</code>, <code>--significance_level</code>, <code>--significanceLevel</code>, <code>--significancelevel</code></td></tr>
</table>

### bound_multiplier

<table>
<tr><td><b>Description</b></td><td>The bound multiple used for adaptive capping. Should be 'adaptive', False or a positive, real number. We strongly recommend always setting it to 'adaptive'. Using a value of 2 as is often done in other configurators is known to be overly aggressive, and will frequently result in high-quality configurations that are incorrectly rejected. This will cause GPS to eliminate large swaths of the configuration space, possibly eliminating all high-quality configurations. If you believe that the running time distribution of your algorithm has substantially heavier tails than an exponential distribution, then you could set this to a large positive integer, <i>e.g.</i>, 200. However, with a value so large you might as well disable adaptive capping by setting it to False. The default is 'adaptive'.</td></tr>
<tr><td><b>Default</b></td><td>adaptive</td></tr>
<tr><td><b>Aliases</b></td><td><code>--bound-multiplier</code>, <code>--bound_multiplier</code>, <code>--boundMultiplier</code>, <code>--boundmultiplier</code>, <code>--bound-mult</code>, <code>--bound_mult</code>, <code>--boundMult</code>, <code>--boundmult</code></td></tr>
</table>

### decay_rate

<table>
<tr><td><b>Description</b></td><td>The decay rate used in GPS's decaying memory heuristic. Larger values mean information will be forgotten slowly, small values mean information will be forgotten quickly. Set this value to 0 if you believe that all of your algorithm's parameters interact strongly. Should be in [0, 0.5]. The default is 0.2</td></tr>
<tr><td><b>Default</b></td><td>0.2</td></tr>
<tr><td><b>Aliases</b></td><td><code>--decay-rate</code>, <code>--decay_rate</code>, <code>--decayRate</code>, <code>--decayrate</code></td></tr>
</table>

### instance_increment

<table>
<tr><td><b>Description</b></td><td>The instance increment controls the number of instances that are queued at one time. By increasing this value GPS will effectively operate on batches of instance_increment instances at one time for its intensification and queuing mechanisms. This can help to make better use of large amounts of parallel resources if the target algorithm runs can be performed very quickly and/or there are few parameters to be optimized. The instance increment must be a positive Fibonacci number. GPS will also dynamically update the value for the instance increment if it observes that there are too few tasks in the queue to keep the workers busy, or if there are too many tasks in the queue for the workers to keep up. The default is 1.</td></tr>
<tr><td><b>Default</b></td><td>1</td></tr>
<tr><td><b>Aliases</b></td><td><code>--instance-increment</code>, <code>--instance_increment</code>, <code>--instanceIncrement</code>, <code>--instanceincrement</code>, <code>--instance-incr</code>, <code>--instance_incr</code>, <code>--instanceIncr</code>, <code>--instanceincr</code></td></tr>
</table>

### minimum_runs

<table>
<tr><td><b>Description</b></td><td>The minimum number of run equivalents on which a configuration must be run before it can be accepted as a new incumbent. This is also the minimum number of run equivalents required before two configurations will be compared to each other using the permutation test. Configurations whose intersection of run equivalents is less than this number will be considered equal. Consequentially, brackets cannot be updated until at least this many runs have been performed for each configuration. Setting this number too large will delay or completely stop GPS from making any progress. However, setting it too small will allow GPS to make mistakes about the relative performance of two configurations with high probability. Ultimately the distribution of running times for your algorithm will impact what should be considered a good setting for you. If you can only afford to perform a single run of GPS, it is safest to set this parameter on the higher side: perhaps 10-25 (provided you can afford at least thousands of target algorithm runs). Otherwise, 5-10 may be reasonable. Should be at least 5. The default is 5.</td></tr>
<tr><td><b>Default</b></td><td>5</td></tr>
<tr><td><b>Aliases</b></td><td><code>--minimum-runs</code>, <code>--minimum_runs</code>, <code>--minimumRuns</code>, <code>--minimumruns</code>, <code>--min-runs</code>, <code>--min_runs</code>, <code>--minRuns</code>, <code>--minruns</code>, <code>--minimum-run-equivalents</code>, <code>--minimum_run_equivalents</code>, <code>--minimumRunEquivalents</code>, <code>--minimumrunequivalents</code>, <code>--min-run-equivalents</code>, <code>--min_run_equivalents</code>, <code>--minRunEquivalents</code>, <code>--minrunequivalents</code>, <code>--minimum-instances</code>, <code>--minimum_instances</code>, <code>--minimumInstances</code>, <code>--minimuminstances</code>, <code>--min-instances</code>, <code>--min_instances</code>, <code>--minInstances</code>, <code>--mininstances</code></td></tr>
</table>

### minimum_workers

<table>
<tr><td><b>Description</b></td><td>GPS must use at least two processes to run: the master process, which loops through each parameter checking for updates and queuing runs; and at least one worker process, which perform target algorithm runs. By default, GPS's master process will setup the scenario files and then wait until it has received a notification that at least one worker is ready to begin. GPS does not count any time while waiting towards its total configuration budget. This parameter controls the minimum number of workers that need to be ready in order for GPS's master process to start. Note that it does not place any restriction on the maximum number of workers. If you set this value to 1, you can still point an unlimitted number of workers to the same GPS ID and they will run. This parameter is only used when starting GPS. If some or all of the workers crash unexpectedly, the master process will continue running until it has exhausted its configuration budget (which may be never if the configuration budget is based on the maximum number of target algorithm runs). This must be a non-negative integer. The default is 1.</td></tr>
<tr><td><b>Default</b></td><td>1</td></tr>
<tr><td><b>Aliases</b></td><td><code>--minimum-workers</code>, <code>--minimum_workers</code>, <code>--minimumWorkers</code>, <code>--minimumworkers</code>, <code>--min-workers</code>, <code>--min_workers</code>, <code>--minWorkers</code>, <code>--minworkers</code></td></tr>
</table>

### parameter_order

<table>
<tr><td><b>Description</b></td><td>Determines whether or not a bandit queue is used to prioritize parameters that are believed to be more importance. Parameter importance is approximated by counting the number of times that a parameter's incumbent is updated. Options are 'BANDIT', 'RANDOM' and 'DETERMINISTIC'. If set to 'RANDOM' or 'DETERMINISTIC' then parameters are prioritized equally, but the order in which they are processed will either be shuffled or not, respectively. Deterministic ordering is useful for debugging as it removes one of the many elements of randomness, but is otherwise not recommended. 'RANDOM' might be preferable to 'BANDIT' for heavily parameterized scenarios containing many conditional parameters -- especially if a single top-level parent parameter controls which of several algorithms are used, when each of which in turn contains many children parameters.</td></tr>
<tr><td><b>Default</b></td><td>BANDIT</td></tr>
<tr><td><b>Aliases</b></td><td><code>--parameter-order</code>, <code>--parameter_order</code>, <code>--parameterOrder</code>, <code>--parameterorder</code></td></tr>
</table>

### post_process_incumbent

<table>
<tr><td><b>Description</b></td><td>GPS can make some mistakes. Most often, these will simply cause GPS to avoid high-quality regions of the configuration space. However, in the presence of parameter interactions some mistakes can cause GPS to return worse incumbents when given a larger budget. This is because GPS can update the incumbent to a configuration which has never been evaluated before. Given enough time, GPS should typically be able to recover from these situations. However, if the configuration run is terminated shortly after such an update, GPS may return a poor quality incumbent configuration. By enabling this feature, GPS will automatically post-process all of the recorded target algorithm runs and select the configuration which exhibits the best performance on the largest number of instances. This post processing is an experimental method for post-processing the output from one or more GPS runs to help protect against these kinds of mistakes made by GPS. However, preliminary results testing this method currently indicates that it typically decreases the performance of the incumbents returned by GPS. Should be 'True' or 'False'. The default is 'False'.</td></tr>
<tr><td><b>Default</b></td><td>False</td></tr>
<tr><td><b>Aliases</b></td><td><code>--post-process-incumbent</code>, <code>--post_process_incumbent</code>, <code>--postProcessIncumbent</code>, <code>--postprocessincumbent</code></td></tr>
</table>

### share_instance_order

<table>
<tr><td><b>Description</b></td><td>GPS randomizes the order in which the configurations are evaluated on instances. Each parameter search process can either share an instance ordering or not. In the original version of GPS the instance ordering was shared, but we suspect it will slightly improve the performance to do otherwise, so the default is False.</td></tr>
<tr><td><b>Default</b></td><td>False</td></tr>
<tr><td><b>Aliases</b></td><td><code>--share-instance-order</code>, <code>--share_instance_order</code>, <code>--shareInstanceOrder</code>, <code>--shareinstanceorder</code></td></tr>
</table>

### sleep_time

<table>
<tr><td><b>Description</b></td><td>When the master or worker processes are blocked waiting for new results/tasks to be pushed to the database, they will sleep for this amount of time, measured in CPU seconds.The default is 0.</td></tr>
<tr><td><b>Default</b></td><td>0.0</td></tr>
<tr><td><b>Aliases</b></td><td><code>--sleep-time</code>, <code>--sleep_time</code>, <code>--sleepTime</code>, <code>--sleeptime</code></td></tr>
</table>

## Post-Process Parameters

GPS comes with a currently-undocumented post-processing procedure that can be used to post-process the output from one or more runs of GPS in order to extract the best configuration that has been evaluated on the largest number of instances. These are the parameters that control the behaviour of this procedure. If you perform multiple independent runs of GPS, but can not afford the time required to validate all of final incumbents, you may find this feature helpful. However, preliminary data suggests that using this procedure to post-process the output of a single GPS run harms the quality of the final configurations. Further study of this method is still required.

### post_process_alpha

<table>
<tr><td><b>Description</b></td><td>The significance level used in the permutation tests performed during GPS's optional incumbent post-processing procedure. Unlike the alpha parameter used by GPS's main procedure, multiple test correction is enabled by default, so this can be viewed as the actual significance level of the statistical tests performed, rather than as a heuristic. As a result, it is not unreasonable to set the main alpha parameter to a larger value than this one -- especially if multiple independent runs of GPS are performed. Should be in (0, 0.25]. The default is 0.05. </td></tr>
<tr><td><b>Default</b></td><td>0.05</td></tr>
<tr><td><b>Aliases</b></td><td><code>--post-process-alpha</code>, <code>--post_process_alpha</code>, <code>--postProcessAlpha</code>, <code>--postprocessalpha</code>, <code>--post-process-significance-level</code>, <code>--post_process_significance_level</code>, <code>--postProcessSignificanceLevel</code>, <code>--postprocesssignificancelevel</code></td></tr>
</table>

### post_process_min_runs

<table>
<tr><td><b>Description</b></td><td>The minimum number of unique instances on which the intersection of the incumbent and a challenger must have been evaluated in order for a challenger to be considered in GPS's optional post-processing, incumbent-selection phase.</td></tr>
<tr><td><b>Default</b></td><td>5</td></tr>
<tr><td><b>Aliases</b></td><td><code>--post-process-min-runs</code>, <code>--post_process_min_runs</code>, <code>--postProcessMinRuns</code>, <code>--postprocessminruns</code>, <code>--post-process-min-instances</code>, <code>--post_process_min_instances</code>, <code>--postProcessMinInstances</code>, <code>--postprocessmininstances</code></td></tr>
</table>

### post_process_multiple_test_correction

<table>
<tr><td><b>Description</b></td><td>Determines whether or not multiple test correction is used during GPS's optional incumbent post-processing procedure. Must be 'True' or 'False'. The default is 'True'.</td></tr>
<tr><td><b>Default</b></td><td>True</td></tr>
<tr><td><b>Aliases</b></td><td><code>--post-process-multiple-test-correction</code>, <code>--post_process_multiple_test_correction</code>, <code>--postProcessMultipleTestCorrection</code>, <code>--postprocessmultipletestcorrection</code></td></tr>
</table>

### post_process_n_permutations

<table>
<tr><td><b>Description</b></td><td>The number of permutations performed by the permutation test during GPS's optional incumbent post-processing procedure. Recommended to be at least 10000 to obtain stable permutation test results. Set it higher if you are using a smaller significance level or are performing the procedure on many combined, independent GPS runs, as the significance level will be smaller in such cases in order to perform multiple test correction. Must be a positive integer greater than 1000. The default is 10000.</td></tr>
<tr><td><b>Default</b></td><td>10000</td></tr>
<tr><td><b>Aliases</b></td><td><code>--post-process-n-permutations</code>, <code>--post_process_n_permutations</code>, <code>--postProcessNPermutations</code>, <code>--postprocessnpermutations</code>, <code>--post-process-number-of-permutations</code>, <code>--post_process_number_of_permutations</code>, <code>--postProcessNumberOfPermutations</code>, <code>--postprocessnumberofpermutations</code></td></tr>
</table>

# Contact

Yasha Pushak  
ypushak@cs.ubc.ca  

PhD Student & Vanier Scholar  
Department of Computer Science  
The University of British Columbia  
