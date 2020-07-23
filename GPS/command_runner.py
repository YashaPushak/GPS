import os

from abstract_runner import AbstractRunner
from gpsHelper import getParamString
import helper

class TargetAlgorithmRunner(AbstractRunner):

    def perform_run(self, parameters, instance, instance_specifics, seed, 
                    cutoff, run_length, run_id, temp_dir='.'):
        command = self._get_command(self._wrapper, parameters, instance, 
                                    instance_specifics, seed, cutoff, 
                                    run_length, run_id, temp_dir)
        os.system(command)
        return read_output_file(_get_output_file(temp_dir, run_id))

    def _get_command(self, wrapper, parameters, instance, instance_specifics, seed, cutoff,
                    run_length, run_id, temp_dir):
        # Returns a command line string for running the algorithm
        output_file = _get_output_file(temp_dir, run_id)
        param_string = getParamString(parameters)
        command = wrapper + ' ' + str(instance) + ' ' + str(instance_specifics) + ' ' + str(cutoff) \
              + ' ' + str(run_length) + ' ' + str(seed) + ' ' + param_string + ' > ' + output_file
        return command

   
def _get_output_file(temp_dir, run_id):
    return temp_dir + '/log-' + run_id + '.log'

def read_output_file(outputFile):
    # Specify inf in case of error or timeout
    runtime = float('inf')
    sol = float('inf')
    res = "CRASHED"
    misc = 'The target algorithm failed to produce output in the expected format'
    if not helper.isFile(outputFile):
        misc = 'The target algorithm failed to produce any output'
    else:
        # Parse the results from the temp file
        with open(outputFile) as f:
            for line in f:
                if("Result for SMAC:" in line
                   or "Result for ParamILS:" in line
                   or "Result for GPS:" in line
                   or "Result for Configurator:" in line):
                    results = line[line.index(":")+1:].split(",")

                    runtime = float(results[1])
                    sol = float(results[2])

                    if ("SAT" in results[0]
                       or "UNSAT" in results[0]
                       or "SUCCESS" in results[0]):
                        res = "SUCCESS"
                    elif("CRASHED" in results[0]):
                        res = "CRASHED"
                    elif("TIMEOUT" in results[0]):
                        res = "TIMEOUT"
                        runtime = float('inf')
                    else:
                        res = "CRASHED"

                    misc = results[-1].strip() + ' - ' + str(results[0])

    os.system('rm ' + outputFile + ' -f')

    return res, runtime, sol, misc

