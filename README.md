# api-nwm-gcp
REST API backed by National Water Model data, developed on Google Cloud Platform. This repository contains general architecture diagram for a general understanding, but it focuses on two GCP products and their respective set up files and configurations: Cloud Functions and API Gateway.

--------------------------------
Google Cloud Function (2nd Gen):
Each Cloud Function (CF) corresponds to one GET gate set up through API Gateway. Each CF contains a main.py file and a requirements.txt file, and its basic settings are:

INITIAL SETUP:
- Trigger: HTTPS / Require authentication (Manage authorized users with Cloud IAM)
- Region: us-central1
- Programming language: Python 3.9

RUNTIME:
- Memory allocated: 256 MB
- CPU: 0.167
- Timeout: 60
- Concurrency: 1
- Autoscaling: 0-100
- Runtime service account: function-to-bigquery@nwm-ciroh.iam.gserviceaccount.com

BUILD:
- Default

CONNECTIONS:
- Ingress settings: Allow all traffic
- Egress settings: None

SECURITY AND IMAGE REPO:
- Encryption: Google-managed encryption key
- Image repository: none

--------------------------------
Google API Gateway:
Composed by YAML config file and gateways. It puts all the different Cloud Functions in a single place (API) and it requests end-user to enter a valid API key for validation. API Gateway also receives variables entered by the end-user and takes them to the Cloud Function invoked by the GET request. 

--------------------------------
Service Account:
function-to-bigquery@nwm-ciroh.iam.gserviceaccount.com is set up to access both BigQuery from Cloud Function and Cloud Function from API Gateway. Permissions: BigQuery Job User & Cloud Run Invoked

--------------------------------
Example calls (Google Cloud Shell):

->Interacting with Cloud Function:

curl -m 70 -X GET https://us-central1-nwm-ciroh.cloudfunctions.net/forecastrecords_1?featureID=[**Insert featureID**] \
-H "Authorization: bearer $(gcloud auth print-identity-token)" \

->Interacting with API Gateway:

curl -X GET "https://api-gateway-get2-9f6idmxh.uc.gateway.dev/forecastrecords?featureID=[**Insert featureID**]" -H "x-api-key: [**Insert API Key**]"

curl -X GET "https://api-gateway-get2-9f6idmxh.uc.gateway.dev/dailyaverages?featureID=[**Insert featureID**]" -H "x-api-key: [**Insert API Key**]"
