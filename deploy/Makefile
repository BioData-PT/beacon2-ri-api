SHELL := /bin/bash

include .env # import DB_PASSWD

all: down up load reindex rebuild

load:
	if [ -z ${DB_PASSWD} ] ; then\
		echo "DB_PASSWD is not set, set it up in the .env file";\
		exit 1;\
	fi

	docker compose exec -e DB_PASSWD=${DB_PASSWD} db bash /mongo-scripts/load.sh
	

load-disney:
	if [ -z ${DB_PASSWD} ] ; then\
		echo "DB_PASSWD is not set, set it up in the .env file";\
		exit 1;\
	fi
	
	docker compose exec -e DB_PASSWD=${DB_PASSWD} db bash /mongo-scripts/load_disney.sh


up-db:
	docker-compose up -d db && \
	docker-compose up -d mongo-express

up: up-db
	docker compose up -d permissions
	docker-compose up -d beacon
	docker-compose up -d ui

rebuild:
	docker-compose rm -sf beacon && \
	docker-compose build beacon && \
	docker-compose up -d beacon && \
	docker-compose logs -f beacon

logs:
	docker-compose logs -f beacon

relaunch:
	docker-compose up beacon

down:
	docker-compose down

verify:
	beacon-verifier http://localhost:5050/api/

reindex:
	#python3 reindex.py
	docker compose exec beacon python3 beacon/reindex.py

mongosh:
	if [ -z ${DB_PASSWD} ] ; then\
		echo "DB_PASSWD is not set, set it up in the .env file";\
		exit 1;\
	fi
	docker compose exec db mongosh beacon -u root -p ${DB_PASSWD} --authenticationDatabase admin

debug:
	docker-compose restart beacon && docker compose logs -f beacon

extract:
	# extract filtering terms
	nohup docker exec beacon python beacon/db/extract_filtering_terms.py &> /tmp/output_extract_filtering_terms.txt &
	
# only works with justfile (https://github.com/casey/just#recipe-parameters)
test COLLECTION REQUEST:
	http POST http://localhost:5050/api/{{COLLECTION}}/ --json < {{REQUEST}}
