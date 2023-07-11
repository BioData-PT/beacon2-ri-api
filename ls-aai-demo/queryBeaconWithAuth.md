# get code:
# go to https://login.gdi.biodata.pt/oidc/auth/authorize?response_type=code&client_id=app-123
# then, paste set the code you got in this command ($code):
curl --location --request POST 'http://login.gdi.biodata.pt/oidc/token' \--header 'Content-Type: application/x-www-form-urlencoded' \--data-urlencode 'grant_type=authorization_code' \--data-urlencode code=$code \--data-urlencode 'client_id=app-123' \--data-urlencode 'client_secret=secret_value' \--data-urlencode 'scope=openid' \
--data-urlencode 'requested_token_type=urn:ietf:params:oauth:token-type:refresh_token'

# get the access_token from that and set it in $accessToken
# first, I need to get a token from mock-aai and put it in $accessToken
curl \
  -H 'Content-Type: application/json' \
  -X POST \
  -H "Authorization: $accessToken" \
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
  http://localhost:5050/api/g_variants/


