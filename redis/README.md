# Setting up a redis database

These instructions help you to setup a simple local database.
You can find more information on redis on their official website: [redis.io](https://redis.io).
The configuration file provided is only a light modification of [the one provided with redis 5.0](https://raw.githubusercontent.com/antirez/redis/5.0/redis.conf).

You first need to install redis. It is available on most systems, as well as on Anaconda using:

    conda install redis 

To start local a server, use the following command:

    redis-server ./redis.conf

This will start a server that listens to port 9503 on your local machine. It has 16 databases with `dbid` from 0 to 15.

In the file `redis_configuration.txt` change `redis-host` to `localhost`

You should now be ready to run GPS.
