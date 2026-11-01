BEGIN;

-- Running upgrade 202610310006 -> 202611010007

ALTER TABLE case_versions ADD COLUMN parent_version_id VARCHAR(36);

ALTER TABLE case_versions ADD CONSTRAINT fk_version_parent FOREIGN KEY(parent_version_id) REFERENCES case_versions (id);

CREATE TABLE case_authorizations (
    id VARCHAR(36) NOT NULL,
    case_id VARCHAR(36) NOT NULL,
    reference VARCHAR(200) NOT NULL,
    scope TEXT NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(case_id) REFERENCES cases (id),
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_case_authorizations_case_id ON case_authorizations (case_id);

CREATE TABLE teaching_copies (
    id VARCHAR(36) NOT NULL,
    version_id VARCHAR(36) NOT NULL,
    authorization_id VARCHAR(36) NOT NULL,
    manifest_key VARCHAR(512) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    review_note TEXT NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    published_by INTEGER NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (version_id),
    FOREIGN KEY(version_id) REFERENCES case_versions (id),
    FOREIGN KEY(authorization_id) REFERENCES case_authorizations (id),
    FOREIGN KEY(published_by) REFERENCES users (id)
);

UPDATE alembic_version SET version_num='202611010007' WHERE alembic_version.version_num = '202610310006';

COMMIT;
