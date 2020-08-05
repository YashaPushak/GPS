class AbstractRunner:
    def _run(self, wrapper, parameters, instance, instance_specifics, seed, cutoff,
             run_length, run_id, temp_dir='.'):
        self._wrapper = wrapper
        result = 'CRASHED'
        runtime_observed = float('inf')
        solution_quality = float('inf')
        misc = 'crashed'
        try:
            result, runtime_observed, solution_quality, misc = self.perform_run(
                parameters=parameters, instance=instance, 
                instance_specifics=instance_specifics, seed=seed, cutoff=cutoff,
                run_length=run_length, run_id=run_id, temp_dir=temp_dir)
        except Exception as error_:
            misc += ' - ' + error_.message 
        command = self._get_command(wrapper, parameters, instance, 
            instance_specifics, seed, cutoff, run_length, run_id, temp_dir)
        return result, runtime_observed, solution_quality, misc, command

    def perform_run(self, parameters, instance, instance_specifics, seed, 
                    cutoff, run_length, run_id, temp_dir='.'):
        """perform_run

        Performs the specified run of the target algorithm and returns the
        results from the run.

        Parameters
        ----------
        parameters : dict
            A dictionary mapping parameter names to values. This defines the
            parameter configuration to be evaluated.
        instance : str
            The name of the instance on which the configuration is to be 
            evaluated. This will correspond directly to one of the lines 
            defined in your instance file.
        instance_specifics : str
            GPS does not currently support instance-specific information. This
            value will always be "0".
        seed : int
            The random seed to be used by your target algorithm.
        cutoff : float
            A running time cutoff to be used by your target algorithm. Note
            that you must enforce this cutoff in your target algorithm or 
            wrapper, GPS does not do it for you. The cutoff time is in seconds.
        run_length : int
            GPS does not currently support run-length-based cutoffs. This value
            will always be 0.
        run_id : str
            A randomly generated string that you may optionally use to uniquely
            identify this run of your target algorithm.
        temp_dir : str
            The location of a directory where temporary files used by your
            target algorithm should be created (and deleted).
        
        Returns
        -------
        result : str
            Should be one of 'SUCCESS', 'TIMEOUT', or 'CRASHED'.
        runtime : float
            The running time used by your target algorithm to perform the run.
            If optimizing for solution quality, this is still used for 
            CPU-time-based configuration budgets.
        solution_quality : float
            The solution quality obtained by your target algorithm on this 
            this instance. If optimizing for running time, this field is
            ignored by GPS (but still required).
        miscellaneous : str
            Miscellaneous data returned by your target algorithm run. This 
            must be comma-free, but otherwise will be ignored by GPS.
        """
        pass
          
    def _get_command(self, wrapper, parameters, instance, instance_specifics, 
                     seed, cutoff, run_length, run_id, temp_dir):
        return ('target_runner.perform_run(parameters={parameters},\n'
                '                          instance=\'{instance}\',\n'
                '                          instance_specifics=\'{instance_specifics}\',\n'
                '                          seed={seed},\n'
                '                          cutoff={cutoff},\n'
                '                          run_length={run_length},\n'
                '                          run_id=\'{run_id}\',\n'
                '                          temp_dir=\'{temp_dir}\')'
                ''.format(parameters=parameters, 
                          instance=instance,
                          instance_specifics=instance_specifics,
                          seed=seed, cutoff=cutoff, run_length=run_length, 
                          run_id=run_id, temp_dir=temp_dir))
 
