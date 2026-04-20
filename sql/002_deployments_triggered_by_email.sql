-- 002_deployments_triggered_by_email.sql
--
-- Changes Deployments.TriggeredBy from INT (originally reserved for an
-- AD user id) to NVARCHAR(256) so it can hold the email returned by
-- auth — matches dev_hub.UserRoles.Email.
--
-- Safe to re-run: the ALTER is idempotent since we explicitly restate
-- the target type. At ship time there were 5 rows with TriggeredBy
-- all NULL, so no data migration was necessary.

USE TOOLBOX;
GO

ALTER TABLE dev_hub.Deployments
    ALTER COLUMN TriggeredBy NVARCHAR(256) NULL;
GO
