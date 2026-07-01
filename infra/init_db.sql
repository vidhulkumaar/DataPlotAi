-- DataPilot AI — Database Initialization
-- Creates the auth and superset databases alongside the main datapilot db

CREATE DATABASE datapilot_auth;
CREATE DATABASE superset;

-- Grant all to the datapilot user
GRANT ALL PRIVILEGES ON DATABASE datapilot TO datapilot;
GRANT ALL PRIVILEGES ON DATABASE datapilot_auth TO datapilot;
GRANT ALL PRIVILEGES ON DATABASE superset TO datapilot;
