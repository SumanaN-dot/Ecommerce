#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
CLUSTER="${CLUSTER:-ecommerce}"
REPO="${REPO:-ecommerce}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
SQL_INSTANCE="${SQL_INSTANCE:-ecommerce-db}"
DOMAIN="${DOMAIN:-shop.example.com}"

gcloud config set project "$PROJECT_ID"
gcloud services enable \
  container.googleapis.com artifactregistry.googleapis.com \
  sqladmin.googleapis.com iamcredentials.googleapis.com

gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"

gcloud container clusters describe "$CLUSTER" --region "$REGION" >/dev/null 2>&1 ||
  gcloud container clusters create-auto "$CLUSTER" --region "$REGION"

gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"

IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/app:$IMAGE_TAG"
gcloud builds submit --tag "$IMAGE" .

gcloud iam service-accounts describe "ecommerce-api@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1 ||
  gcloud iam service-accounts create ecommerce-api

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:ecommerce-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client" >/dev/null

gcloud iam service-accounts add-iam-policy-binding \
  "ecommerce-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:$PROJECT_ID.svc.id.goog[ecommerce/ecommerce-api]" >/dev/null

gcloud compute addresses describe ecommerce-ip --global >/dev/null 2>&1 ||
  gcloud compute addresses create ecommerce-ip --global

cp -R k8s /tmp/ecommerce-k8s
find /tmp/ecommerce-k8s -type f -name '*.yaml' -print0 | xargs -0 sed -i \
  -e "s/PROJECT_ID/$PROJECT_ID/g" \
  -e "s/REGION/$REGION/g" \
  -e "s/SQL_INSTANCE/$SQL_INSTANCE/g" \
  -e "s/IMAGE_TAG/$IMAGE_TAG/g" \
  -e "s/shop.example.com/$DOMAIN/g"

kubectl apply -f /tmp/ecommerce-k8s/00-namespace.yaml
kubectl apply -f /tmp/ecommerce-k8s/01-service-account.yaml
kubectl apply -f /tmp/ecommerce-k8s/02-config.yaml
kubectl apply -f /tmp/ecommerce-k8s/03-deployment.yaml
kubectl apply -f /tmp/ecommerce-k8s/04-service.yaml
kubectl apply -f /tmp/ecommerce-k8s/05-ingress.yaml
kubectl apply -f /tmp/ecommerce-k8s/06-hpa-pdb.yaml

kubectl rollout status deployment/ecommerce-api -n ecommerce
echo "Static IP: $(gcloud compute addresses describe ecommerce-ip --global --format='value(address)')"
