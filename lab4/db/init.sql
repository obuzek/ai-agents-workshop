-- Lab 4: Securing Agent Data
-- Schema for concern storage with Row-Level Security

CREATE TABLE providers (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE provider_patients (
    provider_id TEXT REFERENCES providers(id),
    patient_id TEXT NOT NULL,
    PRIMARY KEY (provider_id, patient_id)
);

CREATE TABLE concerns (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    provider_id TEXT NOT NULL REFERENCES providers(id),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    action TEXT DEFAULT '',
    concern_type TEXT NOT NULL,
    urgency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unresolved',
    onset TEXT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evidence TEXT[] DEFAULT '{}',
    related_message_ids TEXT[] DEFAULT '{}',
    related_lab_dates TEXT[] DEFAULT '{}',
    related_conditions TEXT[] DEFAULT '{}',
    related_encounter_dates TEXT[] DEFAULT '{}'
);

CREATE INDEX idx_concerns_patient ON concerns(patient_id);
CREATE INDEX idx_concerns_provider ON concerns(provider_id);

CREATE TABLE shared_concerns (
    concern_id TEXT REFERENCES concerns(id) ON DELETE CASCADE,
    shared_with TEXT REFERENCES providers(id),
    shared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    shared_by TEXT REFERENCES providers(id),
    PRIMARY KEY (concern_id, shared_with)
);

CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(id),
    patient_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    concern_count INTEGER DEFAULT 0
);

-- Row-Level Security
ALTER TABLE concerns ENABLE ROW LEVEL SECURITY;

CREATE POLICY provider_concern_access ON concerns
    FOR ALL
    USING (
        provider_id = current_setting('app.provider_id', true)
        OR id IN (
            SELECT concern_id FROM shared_concerns
            WHERE shared_with = current_setting('app.provider_id', true)
        )
    );

ALTER TABLE shared_concerns ENABLE ROW LEVEL SECURITY;

CREATE POLICY provider_shared_access ON shared_concerns
    FOR ALL
    USING (
        shared_with = current_setting('app.provider_id', true)
        OR shared_by = current_setting('app.provider_id', true)
    );

-- Application role (non-superuser, so RLS applies)
CREATE ROLE app_user LOGIN PASSWORD 'app_user_dev';
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Seed data
INSERT INTO providers (id, display_name, role) VALUES
    ('dr_kim', 'Dr. Sarah Kim', 'physician'),
    ('nurse_lopez', 'Nurse Jordan Lopez', 'nurse'),
    ('ma_davis', 'MA Riley Davis', 'medical_assistant');

INSERT INTO provider_patients (provider_id, patient_id)
SELECT 'dr_kim', 'patient-' || LPAD(i::text, 3, '0')
FROM generate_series(1, 12) AS i;

INSERT INTO provider_patients (provider_id, patient_id)
SELECT 'nurse_lopez', 'patient-' || LPAD(i::text, 3, '0')
FROM generate_series(1, 6) AS i;

INSERT INTO provider_patients (provider_id, patient_id)
SELECT 'ma_davis', 'patient-' || LPAD(i::text, 3, '0')
FROM generate_series(1, 3) AS i;
