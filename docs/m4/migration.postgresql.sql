-- M4 only; run on M3 revision 202610300005. Prefer alembic upgrade head.
BEGIN;

-- Running upgrade 202610300005 -> 202610310006

ALTER TABLE tasks ADD COLUMN course_id VARCHAR(36);

ALTER TABLE tasks ADD CONSTRAINT fk_tasks_course_id FOREIGN KEY(course_id) REFERENCES courses (id);

CREATE INDEX ix_tasks_course_id ON tasks (course_id);

CREATE TABLE task_classes (
    id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    class_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (task_id, class_id),
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES classes (id)
);

CREATE INDEX ix_task_classes_task_id ON task_classes (task_id);

CREATE TABLE task_rubric_items (
    id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    max_score NUMERIC(7, 2) NOT NULL,
    sort_order INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_rubric_positive CHECK (max_score > 0),
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

CREATE INDEX ix_task_rubric_items_task_id ON task_rubric_items (task_id);

CREATE TABLE submission_grades (
    id VARCHAR(36) NOT NULL,
    submission_id VARCHAR(36) NOT NULL,
    graded_by INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_score NUMERIC(7, 2) NOT NULL,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_grade_nonnegative CHECK (total_score >= 0),
    UNIQUE (submission_id),
    FOREIGN KEY(submission_id) REFERENCES submissions (id),
    FOREIGN KEY(graded_by) REFERENCES users (id)
);

CREATE TABLE submission_grade_items (
    id VARCHAR(36) NOT NULL,
    grade_id VARCHAR(36) NOT NULL,
    rubric_item_id VARCHAR(36) NOT NULL,
    score NUMERIC(7, 2) NOT NULL,
    comment TEXT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (grade_id, rubric_item_id),
    CONSTRAINT ck_grade_item_nonnegative CHECK (score >= 0),
    FOREIGN KEY(grade_id) REFERENCES submission_grades (id) ON DELETE CASCADE,
    FOREIGN KEY(rubric_item_id) REFERENCES task_rubric_items (id)
);

CREATE INDEX ix_submission_grade_items_grade_id ON submission_grade_items (grade_id);

UPDATE alembic_version SET version_num='202610310006' WHERE alembic_version.version_num = '202610300005';

COMMIT;
