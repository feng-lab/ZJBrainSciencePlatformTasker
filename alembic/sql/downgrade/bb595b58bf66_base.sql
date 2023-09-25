-- Running downgrade bb595b58bf66 -> 

DROP TABLE task_run;

DROP TABLE task;

DROP TABLE task_template;

DELETE
FROM alembic_version
WHERE alembic_version.version_num = 'bb595b58bf66';

DROP TABLE alembic_version;

