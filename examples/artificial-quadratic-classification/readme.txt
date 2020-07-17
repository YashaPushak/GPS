This is a simple example scenario that simulates the solution quality of a binary
classifier. It first calculates the ground truth probability for a particular combination
of hyper-parameter settings using the function

    p_errors = ((x0 + x1 - 10)**2 + (x0 - 5)**2 + (x1 - 5)**2)/300

which is minimized by (5, 5). It then simulates random noise due to the particular fold
used for training by drawing a random sample from a normal distribution with
mean `p_errors`. The resulting value is then thresholded to stay within the range [0, 1].
Finally, the variation due to the particular instances used for validation is simulated
by drawing a second random sample from a binomial distribution with 1000 trials with the
prescribed error probability. This is then used to count the percentage of errors 
observed for the particular hyper-parameter configuration on the indicated cross-
validation fold. 

In this scenario, we simulate running times for the target algorithm by drawing from
a normal distribution with mean 5. These running times are only used by GPS when 
determining the configuration budget remaining. 

Note that this scenario should theoretically be more challenging for GPS than the example
scenario provided for minimizing running times. This is because the response observed to
the hyper-parameters does include significant second order effects -- that is, the hyper-
parameters interact somewhat strongly. Nevertheless, even though GPS assumes that these
interactions are not strong, we can still see on this scenario that GPS is often able to
find hyper-parameter configurations that yield close to the optimal error rate of 
0% using as few as 200 target algorithm calls (note that this number counts the number of
of times any hyper-parameter configuration is evaluated on a single cross-validation 
fold, therefore evaluating a single configuration on all 10 folds corresponds to 10
target algorithm calls).
