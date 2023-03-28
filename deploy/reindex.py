from pymongo.mongo_client import MongoClient
import conf
import secret

client = MongoClient(
    "mongodb://{}:{}@{}:{}/{}?authSource={}".format(
        conf.database_user,
        secret.DB_PASSWD,
        #conf.database_host,
        "127.0.0.1",
        conf.database_port,
        conf.database_name,
        conf.database_auth_source,
    )
)

client.beacon.analyses.create_index([("$**", "text")])
client.beacon.biosamples.create_index([("$**", "text")])
client.beacon.cohorts.create_index([("$**", "text")])
client.beacon.datasets.create_index([("$**", "text")])
client.beacon.genomicVariations.create_index([("$**", "text")])
client.beacon.individuals.create_index([("$**", "text")])
client.beacon.runs.create_index([("$**", "text")])
