BEGIN;

-- 删除之前的类型和表

DROP TABLE IF EXISTS task_run;
DROP TABLE IF EXISTS task;
DROP TABLE IF EXISTS task_template;
DROP TABLE IF EXISTS task_interpreter;

DROP TYPE IF EXISTS Status;
DROP TYPE IF EXISTS Type;

-- 创建枚举类型

CREATE TYPE Type AS ENUM ('python', 'nodejs');

CREATE TYPE Status AS ENUM ('pending', 'running', 'success', 'failed', 'canceled');

-- 创建表

CREATE TABLE task_interpreter
(
    id          SERIAL       NOT NULL,
    create_at   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted  BOOLEAN                     NOT NULL DEFAULT FALSE,
    name        VARCHAR(255) NOT NULL,
    type        Type         NOT NULL,
    executable JSON NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE task_template
(
    id          SERIAL       NOT NULL,
    create_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    modified_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    is_deleted  BOOLEAN                     DEFAULT FALSE,
    name        VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL,
    executable  JSON         NOT NULL,
    environment JSON         NOT NULL,
    interpreter INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT fk_task_template_task_interpreter_id_interpreter FOREIGN KEY (interpreter) REFERENCES task_interpreter (id)
);

CREATE TABLE task
(
    id          SERIAL       NOT NULL,
    create_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    modified_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    is_deleted  BOOLEAN                     DEFAULT FALSE,
    name        VARCHAR(255) NOT NULL,
    argument    JSON         NOT NULL,
    environment JSON         NOT NULL,
    retry_times INTEGER      NOT NULL,
    template    INTEGER      NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_task_task_template_id_template FOREIGN KEY (template) REFERENCES task_template (id)
);

CREATE TABLE task_run
(
    id          SERIAL  NOT NULL,
    create_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    modified_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    is_deleted  BOOLEAN                     DEFAULT FALSE,
    index       INTEGER NOT NULL,
    status      Status  NOT NULL,
    start_at    TIMESTAMP WITHOUT TIME ZONE,
    end_at      TIMESTAMP WITHOUT TIME ZONE,
    task        INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_task_run_task_id_task FOREIGN KEY (task) REFERENCES task (id)
);

-- 自动更新 modified_at 字段

CREATE OR REPLACE FUNCTION update_modified_at()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.modified_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_task_interpreter_modified_at
    BEFORE UPDATE
    ON task_interpreter
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_template_modified_at
    BEFORE UPDATE
    ON task_template
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_modified_at
    BEFORE UPDATE
    ON task
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_run_modified_at
    BEFORE UPDATE
    ON task_run
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

COMMIT;
