This is a simple example scenario that simulates the running times of an algorithm
by first drawing from a normal distribution to determine the difficulty of an instance
and then using that instance's difficulty as the mean of an exponential distribution
used to simulate the running time distribution of the target algorithm on that particular
instance. By simulating an algorithm in this way, you can quickly verify that you have
correctly installed GPS by running this scenario. It should be able to run in less than 5
minutes.

Since many NP-hard and NP-complete algorithms are known to have running time
distributions that are approximately exponential, this should provide running time 
distributions that are approximately realistic. However, the true distribution of
running times between instances in any given instance set is likely to vary substantially
between different instance sets, hence our assumption of normality may not be entirely
realistic.

The artificial algorithm has three simulated parameters designed such that they
are independent from each other. Since GPS assumes most parameters do no interact 
strongly, GPS should be able to perform well on this benchmark with high probability.
Each of the three parameters are modeled by simple functions with minima 1. The effect
of the three parameters is the multiple together with the raw running time sampled as
described above. 

The first parameter, x0, is merely a quadratic function
(x0 - 5)**2 + 1
that is restricted to integer values in [0, 20]. The default is 2 and the argminimum is 5.

The second parameter, x1, is designed to reflect our intuition regarding
the shape of many algorithms' parameter responses. It takes the form
1/x1 + x1 - 1
and it allowed to take on any real value in [0, 20]. The default is 3 and the argminimum
is 1.

The third parameter, heuristic, is a categorical parameter that simulates selecting
between three possible heuristics in the algorithm, 'a', 'b' or 'c'. When set to 'a',
it returns 1, when set to 'b' it returns 20 and when set to 'c' it returns '3'.
The default is 'c' and the argminimum is 'a'.

When using GPS, it is best to choose a running time cutoff for your target algorithm
that allows the default configuration of your algorithm to solve most instances in 
your instance set with high probability (say 90%). If your algorithm is not able to solve
a large fraction of the instances with high probability, then GPS may start to make
mistakes due to a small number of runs of high-quality configurations that get incorrectly
rejected because they exceeded their running time cutoff. When this happens in GPS, it can
eliminate an entire region of the configuration space that contains the global optimum.
For this scenario, you should see that GPS finds configurations within 1% of optimal
about 64% of the time and it should find confiugrations within 10% of optimal about 27% of
the time. You may also observe that in about 9% of the runs, GPS appears to completely
miss high quality values for some of the parameters. These can be attributed to GPS
observing such unlucky runs and incorrectly rejecting high quality regions of the 
configuration space. If you try decreasing the running time cutoff used by GPS in this 
scenario from 10 minutes to 5 minutes, you will notice that the fraction of times GPS
yeilds poor results will increase substantially. As a result, it is never a bad idea to
perform 10-20 runs of your target algorithm with the default configuration on randomly 
chosen training instances prior to choosing the running time cutoff. 

Given enough time, GPS should be able to recover from these kind of mistakes;
however, we instead recommend to always perform at least 3 independent runs of GPS,
either sequentially or in parallel, and then to validate the final incumbents by running
them on the training instance set to pick the best one.
