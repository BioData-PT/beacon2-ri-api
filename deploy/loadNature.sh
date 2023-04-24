natureData=/home/ubuntu/beacon/natureDataFiles
metadataDir=$natureData/mappingMar27metadata/
genomicDataDir=$natureData/genomicData
#metadataDir=data/mydata/cineca
#genomicDataDir=data/mydata/cineca

DB_PASSWD="example"
source secret.py # import db passwd

mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/analyses*.?son --collection analyses
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/biosamples*.?son --collection biosamples
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/cohorts*.?son --collection cohorts
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/datasets*.?son --collection datasets
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/individuals*.?son --collection individuals
mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $metadataDir/runs*.?son --collection runs

mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $genomicDataDir/genomicVariations*.?son --collection genomicVariations
#mongoimport --jsonArray --uri "mongodb://root:$DB_PASSWD@127.0.0.1:27017/beacon?authSource=admin" --file $genomicDataDir/genomicVariations*.json.gz --collection genomicVariations

