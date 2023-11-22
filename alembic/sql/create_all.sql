BEGIN;

-- 删除之前的类型和表

DROP TABLE IF EXISTS run;
DROP TABLE IF EXISTS task;
DROP TABLE IF EXISTS template;
DROP TABLE IF EXISTS interpreter;

DROP TYPE IF EXISTS Status;
DROP TYPE IF EXISTS Type;

-- 创建枚举类型

CREATE TYPE Type AS ENUM ('system_executable', 'executable', 'python', 'nodejs');

CREATE TYPE Status AS ENUM ('pending', 'running', 'success', 'failed', 'canceled');

-- 创建表

CREATE TABLE interpreter
(
    id                   SERIAL PRIMARY KEY,
    create_at            TIMESTAMP    NOT NULL DEFAULT NOW(),
    modified_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    is_deleted           BOOLEAN      NOT NULL DEFAULT FALSE,
    name                 VARCHAR(255) NOT NULL,
    description          TEXT         NOT NULL,
    creator              INTEGER      NOT NULL,
    type                 Type         NOT NULL,
    executable_pack_path VARCHAR(255) NULL,
    executable_path      VARCHAR(255) NULL,
    environment          JSONB        NOT NULL
);

CREATE TABLE template
(
    id               SERIAL PRIMARY KEY,
    create_at        TIMESTAMP DEFAULT NOW(),
    modified_at      TIMESTAMP DEFAULT NOW(),
    is_deleted       BOOLEAN   DEFAULT FALSE,
    name             VARCHAR(255) NOT NULL,
    description      TEXT         NOT NULL,
    script_pack_path VARCHAR(255) NULL,
    script_path      VARCHAR(255) NULL,
    arguments        JSONB        NOT NULL,
    environment      JSONB        NOT NULL,
    interpreter      INTEGER      NOT NULL REFERENCES interpreter (id)
);

CREATE TABLE task
(
    id              SERIAL PRIMARY KEY,
    create_at       TIMESTAMP DEFAULT NOW(),
    modified_at     TIMESTAMP DEFAULT NOW(),
    is_deleted      BOOLEAN   DEFAULT FALSE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT         NOT NULL,
    creator         INTEGER      NOT NULL,
    depends         JSONB        NOT NULL,
    status          Status       NOT NULL,
    start_at        TIMESTAMP    NULL,
    end_at          TIMESTAMP    NULL,
    source_file_dir VARCHAR(255) NULL,
    output_file_dir VARCHAR(255) NULL,
    arguments       JSONB        NOT NULL,
    environment     JSONB        NOT NULL,
    user_data       JSONB        NOT NULL,
    template        INTEGER      NOT NULL REFERENCES template (id)
);

CREATE TABLE run
(
    id          SERIAL PRIMARY KEY,
    create_at   TIMESTAMP DEFAULT NOW(),
    modified_at TIMESTAMP DEFAULT NOW(),
    is_deleted  BOOLEAN   DEFAULT FALSE,
    index       INTEGER   NOT NULL,
    status      Status    NOT NULL,
    start_at    TIMESTAMP NULL,
    end_at      TIMESTAMP NULL,
    task        INTEGER   NOT NULL REFERENCES task (id)
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
    ON interpreter
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_template_modified_at
    BEFORE UPDATE
    ON template
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_modified_at
    BEFORE UPDATE
    ON task
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

CREATE TRIGGER update_task_run_modified_at
    BEFORE UPDATE
    ON run
    FOR EACH ROW
EXECUTE FUNCTION update_modified_at();

COMMIT;
