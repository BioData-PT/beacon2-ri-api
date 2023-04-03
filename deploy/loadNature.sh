natureData=/home/ubuntu/beacon/natureDataFiles
metadataDir=$natureData/mappingMar27metadata/
genomicDataDir=$natureData/genomicData

DB_PASSWD="Wk3vjWScUaukdSJ62LJFnpgHK8AaBdJ2um8s2528me3"

mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/analyses*.json --collection analyses
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/biosamples*.json --collection biosamples
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/cohorts*.json --collection cohorts
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/datasets*.json --collection datasets
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/individuals*.json --collection individuals
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/runs*.json --collection runs

mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $genomicDataDir/genomicVariations*.json --collection genomicVariations
#mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $genomicDataDir/genomicVariations*.json.gz --collection genomicVariations

