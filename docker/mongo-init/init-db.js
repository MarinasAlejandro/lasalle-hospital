// Initialize hospital database, collections, and indexes
db = db.getSiblingDB('hospital');

// Create collections explicitly
db.createCollection('patients');
db.createCollection('pipeline_runs');
db.createCollection('rejected_records');

// Unique index on external_id for patients (idempotent upserts)
db.patients.createIndex({ external_id: 1 }, { unique: true });

// Index on pipeline_run_id for rejected_records lookups
db.rejected_records.createIndex({ pipeline_run_id: 1 });

// Index on status for pipeline_runs queries
db.pipeline_runs.createIndex({ status: 1 });
db.pipeline_runs.createIndex({ started_at: -1 });

print('Hospital database initialized: collections and indexes created.');
