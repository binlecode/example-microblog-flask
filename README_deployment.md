## deployment notes

Deployment of application and infrastructure dependencies are based on docker containers.

Major components are:

- microblog web app stack
- microblog background worker stack
- mysql database
- redis queue
- elasticsearch

#### mysql

```sh
docker run --name mysql-microblog -d \
  -e MYSQL_RANDOM_ROOT_PASSWORD=yes \
  -e MYSQL_DATABASE=microblog \
  -e MYSQL_USER=microblog \
  -e MYSQL_PASSWORD=mbmysql123! \
  mysql/mysql-server:latest
```

check mysql conn:

```sh
# run this from a UTM vm docker host where gw IP is 172.17.0.1
mysql -h 172.17.0.2 -umicroblog -p<pswd>
```

#### redis

```sh
docker pull redis:6.2-alpine
docker run --name redis -d -p 6379:6379 redis:6.2-alpine
```

Use telnet to test redis connection:

```shell
telnet 127.0.0.1 6379

Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.
ping
+PONG
^]

telnet> quit
```

#### elasticsearch

https://www.elastic.co/guide/en/elasticsearch/reference/8.0/docker.html

First increase `vm.max_map_count=262144` in `/etc/sysctl.conf` file.

```sh
docker network create elastic
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.0.0
docker run --name es-node01 --net elastic -p 9200:9200 -p 9300:9300 -it \
    docker.elastic.co/elasticsearch/elasticsearch:8.0.0

docker exec -it es-node01 /bin/bash
```

```sh
docker exec -it es-node01 bin/elasticsearch-reset-password -u elastic
Password for the [elastic] user successfully reset.
New value: nM_mncb2utNm+qhFl1MD

# test connection with curl
docker cp es-node01:/usr/share/elasticsearch/config/certs/http_ca.crt .
curl --cacert http_ca.crt -u elastic https://localhost:9200
```

Elasticsearch container takes too much memory on host docker in local computer or UTM vm. Kibana container is not run to
save memory.

#### microblog web stack

```sh
docker build -t microblog:latest .
# check built image
docker image inspect microblog
```

By default elasticsearch is disabled, therefore only mysql and redis are configured in environment variables.

```sh
# remove --rm and add -d to run container in detached mode

# run with elasticsearch disabled
docker run --name microblog -p 8000:5000 --rm \
  -e SECRET_KEY=microblog-secret-key \
  --link mysql-microblog:db-server \
  -e DATABASE_URL='mysql+pymysql://microblog:mbmysql123!@db-server/microblog' \
  --link redis:redis-server \
  -e REDIS_URL=redis://redis-server:6379/0 \
  microblog:latest

# Run with elasticsearch enabled
# Because elasticsearch container es-node01 is in a different docker network
# `elastic`, it needs to be linked to default network `bridge` where other 
# containers are.
# check all docker networks
docker network ls
# connect es-node01 to default network so it is linkable
docker network connect bridge es-node01

# run container with elasticsearch env vars
docker run --name microblog -p 8000:5000 --rm \
  -e SECRET_KEY=microblog-secret-key-that-nobody-knows \
  --link mysql-microblog:db-server \
  -e DATABASE_URL='mysql+pymysql://microblog:mbmysql123!@db-server/microblog' \
  --link redis:redis-server \
  -e REDIS_URL=redis://redis-server:6379/0 \
  --link es-node01:es-server \
  -e ENABLE_ELASTICSEARCH=True \
  -e ELASTICSEARCH_URL=https://es-server:9200 \
  -e ELASTICSEARCH_USER=elastic \
  -e ELASTICSEARCH_PASSWORD=nM_mncb2utNm+qhFl1MD \
  microblog:latest
```

#### microblog RQ worker

```shell
docker run --name rq-worker --rm \
  -e SECRET_KEY=rq-worker-secret-key-that-nobody-knows \
  --link mysql-microblog:db-server \
  -e DATABASE_URL='mysql+pymysql://microblog:mbmysql123!@db-server/microblog' \
  --link redis:redis-server \
  -e REDIS_URL=redis://redis-server:6379/0 \
  --entrypoint venv/bin/rq \
  microblog:latest worker -u redis://redis-server:6379/0 microblog-tasks
```

## docker-compose that combines all containers

Docker-compose can be used to bundle all containers into one deployment yaml
file [docker-compose.yml](./docker-compose.yml).

Notes for the yaml configure file:

- use 'depends_on' to ensure container ordering
- worker container use latest built image with overriden CMD
- worker container depends on web container to initialize and migrate database
- the web container is configured to always build image, alternatively, it can use the latest image the same as worker
- elasticsearch is not enabled in this compose configuration

```sh
docker-compose up
# in detached mode
docker-compose up -d
# stop 
docker-compose down
```

