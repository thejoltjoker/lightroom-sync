-- Create catalogs table
CREATE TABLE IF NOT EXISTS catalogs(
    catalog_id INTEGER PRIMARY KEY,
    catalog_name TEXT NOT NULL UNIQUE,
    last_sync INTEGER
);

-- Create paths table
CREATE TABLE IF NOT EXISTS paths(
    path_id INTEGER PRIMARY KEY,
    path text UNIQUE,
    catalog_id INTEGER,
    FOREIGN KEY(catalog_id) REFERENCES catalogs(catalog_id)
);

-- Select all tables
SELECT name FROM sqlite_master WHERE type = 'table';

-- Insert catalog
INSERT INTO catalogs(catalog_name, latest_version)
VALUES ('test_catalog', '13');

-- Insert catalog if it doesn't exist
INSERT INTO catalogs(catalog_name, latest_version)
SELECT 'test_catalog2', 13
WHERE NOT EXISTS (SELECT * FROM catalogs WHERE catalog_name = 'test_catalog2');


-- Insert path
INSERT INTO paths(path, catalog_id)
SELECT '/Users/johannes/Dropbox/Pictures/lightroom/catalogs/2013/lightroom_2013_003.lrcat', 1
WHERE NOT EXISTS (SELECT * FROM paths
WHERE path = '/Users/johannes/Dropbox/Pictures/lightroom/catalogs/2013/lightroom_2013_003.lrcat');

-- Display path based on catalog_id
SELECT path FROM paths
WHERE catalog_id = 13;

-- Get id from catalog name
SELECT catalog_id FROM catalogs
WHERE catalog_name = 'lr_classic_2013_011';


-- Select all paths with catalog id
SELECT * FROM paths
WHERE catalog_id = 1

-- Drop tables
DROP TABLE IF EXISTS paths;
DROP TABLE IF EXISTS catalogs;


-- Delete catalog
DELETE FROM catalogs
WHERE catalog_name = 'test_catalog';

-- Delete all paths
DELETE FROM paths;



-- Select all paths based on catalog name
SELECT * FROM paths
WHERE catalog_id = (SELECT catalog_id FROM catalogs WHERE catalog_name = 'lr_classic_2019_v001');


-- Update last sync date
UPDATE catalogs
SET last_sync = 123
WHERE catalog_name = 'lr_classic_2013_006';