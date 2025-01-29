# Deployment instructions

[![](https://mermaid.ink/img/pako:eNp1U01vgzAM_Ssop01qdtiRw6RRWm1SD91WJk2lhxRMGw0SFEg_VvW_z4EE2pX15Lz3bD_b9EQSmQLxyUaxcuvN3mPh4S-qQC0z5meMagyb98pSr5bYc5HKPS3YgRf8B5Cwiue5k2DWDrNfFou5QS0fBneWT1nN1qwCL7TB6j4WVoTI8ktq5RmRzRzLotR1Zy2F6ruWZQdb1eSQQG4lGc-BggFa2Eo-x1NXQzDzsngwnV4kmufKGar0ut3RmwZ1bDG3Ko_SJ5y_B52jhsDJe6aPuoJrYIkU9PHh0JN2j01-GFzjYXBbFkTqjA7VrhXjgosN1fy6VvR_jei2u-0cDc5j9WYfPehmcAtpmYtOnVNzcG8mWYo2Lzoa1BRorjc0YJbRHcs5fiVSXc_WpDTJeMfBTeLhHf9nDTYgI1KAKhhP8S9yMnBM6i0UEBMfQwEaN5vHJBZnlOoSXcAk5WiF-LXSMCJM1_LjKBL3bjUhZ2i_aMHzL0zOAvw)](https://mermaid.live/edit#pako:eNp1U01vgzAM_Ssop01qdtiRw6RRWm1SD91WJk2lhxRMGw0SFEg_VvW_z4EE2pX15Lz3bD_b9EQSmQLxyUaxcuvN3mPh4S-qQC0z5meMagyb98pSr5bYc5HKPS3YgRf8B5Cwiue5k2DWDrNfFou5QS0fBneWT1nN1qwCL7TB6j4WVoTI8ktq5RmRzRzLotR1Zy2F6ruWZQdb1eSQQG4lGc-BggFa2Eo-x1NXQzDzsngwnV4kmufKGar0ut3RmwZ1bDG3Ko_SJ5y_B52jhsDJe6aPuoJrYIkU9PHh0JN2j01-GFzjYXBbFkTqjA7VrhXjgosN1fy6VvR_jei2u-0cDc5j9WYfPehmcAtpmYtOnVNzcG8mWYo2Lzoa1BRorjc0YJbRHcs5fiVSXc_WpDTJeMfBTeLhHf9nDTYgI1KAKhhP8S9yMnBM6i0UEBMfQwEaN5vHJBZnlOoSXcAk5WiF-LXSMCJM1_LjKBL3bjUhZ2i_aMHzL0zOAvw)

Files that you need to change (look at the \*.example files!):
- .env  (define the password for the db user, only use letters and numbers)
- beacon2-ri-api/training-ui-files/secret.py (use the script in the same directory to generate a key)

You need to run reindex.py everytime you recreate your DB (you can run it on the beacon container or on the host):
	- To run on container: `docker compose exec beacon python3 beacon/reindex.py`
	- To run on host: `python3 reindex.py` # you need to download the appropriate python modules

Additional configurations:

- Nginx:
    - When the containers for the API and UI are up and running you may want to make them available for external use over HTTPS, for that install nginx and use the configuration that better suits you on nginx_confs directory. 
    - Use the simple.conf file if you only intend to have a Beaconv2 running, beacon_w_test is used if you also configure a test environment running on another instance, in that case the other instance needs to use the beacon_test_instance config.
    - You'll need to change the server name and the paths to the certificates.
    - Careful with the favicon.ico path (it is in beacon2-ri-api/deploy by default). Nginx user (www-data) needs to have read permissions on it and execute permissions on **ALL** the directories in the path.

## Prerequisites

You should have installed:

- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/installation/installation/) (specifically `mongoimport` to add the dummy data to the database)
- [Python 3](https://www.python.org/downloads/)

## Installation

All of the commands should be executed from the deploy directory.

```bash
cd deploy
```

### Light up the database and the Beacon

#### Up the containers

```bash
docker-compose up -d --build
```

With `mongo-express` we can see the contents of the database at [http://localhost:8081](http://localhost:8081).

#### Load the data

To load the database we execute the following commands:

```bash
docker cp /path/to/analyses.json deploy_db_1:tmp/analyses.json
docker cp /path/to/biosamples.json deploy_db_1:tmp/biosamples.json
docker cp /path/to/cohorts.json deploy_db_1:tmp/cohorts.json
docker cp /path/to/datasets.json deploy_db_1:tmp/datasets.json
docker cp /path/to/genomicVariationsVcf.json deploy_db_1:tmp/genomicVariations.json
docker cp /path/to/individuals.json deploy_db_1:tmp/individuals.json
docker cp /path/to/runs.json deploy_db_1:tmp/runs.json
```

```bash
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/datasets.json --collection datasets
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/analyses.json --collection analyses
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/biosamples.json --collection biosamples
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/cohorts.json --collection cohorts
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/genomicVariations.json --collection genomicVariations
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/individuals.json --collection individuals
docker exec deploy_db_1 mongoimport --jsonArray --uri "mongodb://root:example@127.0.0.1:27017/beacon?authSource=admin" --file /tmp/runs.json --collection runs
```

This loads the JSON files inside of the `data` folder into the MongoDB database container.

#### Create the indexes

You can create the necessary indexes running the following Python script:

```bash
docker exec beacon python beacon/reindex.py
```

#### Fetch the ontologies and extract the filtering terms

> This step consists of analyzing all the collections of the Mongo database for first extracting the ontology OBO files and then filling the filtering terms endpoint with the information of the data loaded in the database.∫

You can automatically fetch the ontologies and extract the filtering terms running the following script:

```bash
docker exec beacon python beacon/db/extract_filtering_terms.py
```

#### Get descendant and semantic similarity terms

**If you have the ontologies loaded and the filtering terms extracted**, you can automatically get their descendant and semantic similarity terms running the following script:

```bash
docker exec beacon python beacon/db/get_descendants.py
```

#### Check the logs

Check the logs until the beacon is ready to be queried:

```bash
docker-compose logs -f beacon
```

## Usage

You can query the beacon using GET or POST. Below, you can find some examples of usage:

> For simplicity (and readability), we will be using [HTTPie](https://github.com/httpie/httpie).

### Using GET

Querying this endpoit it should return the 13 variants of the beacon (paginated):

```bash
http GET http://localhost:5050/api/g_variants
```

You can also add [request parameters](https://github.com/ga4gh-beacon/beacon-v2-Models/blob/main/BEACON-V2-Model/genomicVariations/requestParameters.json) to the query, like so:

```bash
http GET http://localhost:5050/api/individuals?filters=NCIT:C16576,NCIT:C42331
```

### Using POST

You can use POST to make the previous query. With a `request.json` file like this one:

```json
{
    "meta": {
        "apiVersion": "2.0"
    },
    "query": {
        "requestParameters": {
    "alternateBases": "G" ,
    "referenceBases": "A" ,
"start": [ 16050074 ],
            "end": [ 16050568 ],
	    "variantType": "SNP"
        },
        "filters": [],
        "includeResultsetResponses": "HIT",
        "pagination": {
            "skip": 0,
            "limit": 10
        },
        "testMode": false,
        "requestedGranularity": "record"
    }
}

```

You can execute:

```bash
curl \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "meta": {
        "apiVersion": "2.0"
    },
    "query": {
        "requestParameters": {
    "alternateBases": "G" ,
    "referenceBases": "A" ,
"start": [ 16050074 ],
            "end": [ 16050568 ],
	    "variantType": "SNP"
        },
        "filters": [],
        "includeResultsetResponses": "HIT",
        "pagination": {
            "skip": 0,
            "limit": 10
        },
        "testMode": false,
        "requestedGranularity": "record"
    }
}' \
  http://localhost:5050/api/g_variants


```

But you can also use complex filters:

```json
{
    "meta": {
        "apiVersion": "2.0"
    },
    "query": {
        "filters": [
            {
                "id": "UBERON:0001256",
                "scope": "biosamples",
                "includeDescendantTerms": false
            }
        ],
        "includeResultsetResponses": "HIT",
        "pagination": {
            "skip": 0,
            "limit": 10
        },
        "testMode": false,
        "requestedGranularity": "count"
    }
}
```

You can execute:

```bash
http POST http://localhost:5050/api/biosamples --json < request.json
```

And it will use the ontology filter to filter the results.

## Privacy Strategy

To use the privacy strategy based on the budget strategy from Raisaro et al., you need to run the following command:

```bash
docker compose exec beacon python /beacon/deploy/mongo-scripts/update_allele_frequencies.py
```

This command will populate the database with the allele frequency information for each variant, to be used in the privacy strategy. You must run it before using Beacon.
