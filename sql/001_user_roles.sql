-- 001_user_roles.sql
--
-- Creates dev_hub.UserRoles — the authorization table for DevHub.
-- Email (from AAD token's preferred_username / upn, lowercased) is PK.
-- Role is a soft enum enforced via CHECK constraint.
--
-- Run once against TOOLBOX. Idempotent: re-running does nothing if the
-- table already exists.

USE TOOLBOX;
GO

IF NOT EXISTS (
    SELECT 1
    FROM   INFORMATION_SCHEMA.TABLES
    WHERE  TABLE_SCHEMA = 'dev_hub'
      AND  TABLE_NAME   = 'UserRoles'
)
BEGIN
    CREATE TABLE dev_hub.UserRoles (
        Email        NVARCHAR(256) NOT NULL PRIMARY KEY,
        Role         NVARCHAR(32)  NOT NULL CHECK (Role IN ('viewer', 'admin')),
        CreatedAt    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
        CreatedBy    NVARCHAR(256) NULL,
        Notes        NVARCHAR(512) NULL
    );
END
GO

-- Seed the initial admin (Tyler). Idempotent via MERGE.
MERGE dev_hub.UserRoles AS target
USING (SELECT 'tylere@metalsfab.com' AS Email) AS src
    ON target.Email = src.Email
WHEN NOT MATCHED THEN
    INSERT (Email, Role, CreatedBy, Notes)
    VALUES ('tylere@metalsfab.com', 'admin', 'bootstrap', 'Initial admin seed');
GO
