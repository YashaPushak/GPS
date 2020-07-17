# GPS
The Golden Parameter Search Configurator

This is the exact copy of GPS that was used to perform the experiments reported
in the 2020 GECCO paper "Golden Parameter Search: Exploiting Structure to 
Quickly Configuration Parameters in Parallel". We strongly recommend you use the
version of GPS available in `master` instead of this version. This version is
almost entirely undocumented and does not use the same command line interface 
as the version in `master`.

Other than this, the two versions are nearly identical, except that the latest
version of GPS includes more features and a few other slight improvements. If 
you really want to compare against this exact version of GPS, we still 
recommend to use the other version; however, you should take a look at the
 parameter `share_instance_order`, since it defaults to a value other than the
 one which is hard-coded into this version of GPS. (This information is 
documented in `README.md` in `master`.)
