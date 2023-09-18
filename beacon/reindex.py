from pymongo.mongo_client import MongoClient
from pymongo import ASCENDING
import conf
import os

DB_PASSWD = os.getenv("DB_PASSWD", "example")

client = MongoClient(
    "mongodb://{}:{}@{}:{}/{}?authSource={}".format(
        conf.database_user,
        DB_PASSWD,
        conf.database_host,
        conf.database_port,
        conf.database_name,
        conf.database_auth_source,
    )
)
print("*** Starting to reindex... ***")
client.beacon.analyses.create_index([("$**", "text")])
client.beacon.biosamples.create_index([("$**", "text")])
client.beacon.cohorts.create_index([("$**", "text")])
client.beacon.datasets.create_index([("$**", "text")])
client.beacon.genomicVariations.create_index([("$**", "text")])
client.beacon.individuals.create_index([("$**", "text")])
client.beacon.runs.create_index([("$**", "text")])

# custom indexes
client.beacon.genomicVariations.create_index([
        ("_info.datasetId", ASCENDING),
        ("_position.refseqId", ASCENDING),
        ("variation.referenceBases", ASCENDING),
        ("variation.alternateBases", ASCENDING),
        ("_position.start", ASCENDING)
    ],
    name="genomic variation & region query"
)
print("*** Reindex completed OK! ***")
