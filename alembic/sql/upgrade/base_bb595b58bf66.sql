CREATE TABLE alembic_version
(
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> bb595b58bf66

CREATE TABLE task_template
(
    id          BIGINT         NOT NULL,
    create_at   DATETIME DEFAULT (CURRENT_TIMESTAMP),
    modified_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    is_deleted  BOOLEAN  DEFAULT 0,
    name        VARCHAR(255)   NOT NULL,
    type        VARCHAR(10)    NOT NULL,
    executable  VARCHAR(65535) NOT NULL,
    argument    JSON           NOT NULL,
    environment JSON           NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE task
(
    id           BIGINT       NOT NULL,
    create_at    DATETIME DEFAULT (CURRENT_TIMESTAMP),
    modified_at  DATETIME DEFAULT (CURRENT_TIMESTAMP),
    is_deleted   BOOLEAN  DEFAULT 0,
    name         VARCHAR(255) NOT NULL,
    creator_id   BIGINT       NOT NULL,
    source_files JSON         NOT NULL,
    retry_times  INTEGER      NOT NULL,
    template     BIGINT,
    PRIMARY KEY (id),
    CONSTRAINT fk_task_task_template_id_template FOREIGN KEY (template) REFERENCES task_template (id)
);

CREATE TABLE task_run
(
    id          BIGINT     NOT NULL,
    create_at   DATETIME DEFAULT (CURRENT_TIMESTAMP),
    modified_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    is_deleted  BOOLEAN  DEFAULT 0,
    status      VARCHAR(8) NOT NULL,
    start_at    DATETIME,
    end_at      DATETIME,
    task        BIGINT,
    PRIMARY KEY (id),
    CONSTRAINT fk_task_run_task_id_task FOREIGN KEY (task) REFERENCES task (id) ON DELETE CASCADE ON UPDATE CASCADE
);

INSERT INTO alembic_version (version_num)
VALUES ('bb595b58bf66');
