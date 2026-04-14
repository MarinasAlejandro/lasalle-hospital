#!/bin/sh
# Wait for MinIO to be ready
until mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} > /dev/null 2>&1; do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

# Create buckets if they don't exist
mc mb --ignore-existing local/${MINIO_BUCKET_RADIOGRAPHIES}
mc mb --ignore-existing local/${MINIO_BUCKET_RAW_BACKUPS}

echo "MinIO buckets initialized: ${MINIO_BUCKET_RADIOGRAPHIES}, ${MINIO_BUCKET_RAW_BACKUPS}"
