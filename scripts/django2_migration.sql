-- These should be applied before running `./manage.py migrate`

-- A few test accounts where the user was (manually?) deleted from `auth_user`
BEGIN TRANSACTION;
DELETE FROM `social_auth_usersocialauth` WHERE id=854;
DELETE FROM `conference_attendeeprofile` WHERE user_id=1880;
DELETE FROM `conference_attendeeprofile` WHERE user_id=1896;
DELETE FROM `conference_attendeeprofile` WHERE user_id=2097;
DELETE FROM `p3_p3profile` WHERE profile_id=1880;
DELETE FROM `p3_p3profile` WHERE profile_id=1896;
DELETE FROM `p3_p3profile` WHERE profile_id=2097;
END TRANSACTION;

BEGIN TRANSACTION;
-- Data for the below tables causes issues for the Django migrations
-- We dump the data and then reimport it after the migrations are done

-- Export data for conference_vototalk and delete data before migration
.mode insert conference_vototalk
.out /tmp/conference_vototalk.sql
SELECT * FROM conference_vototalk;

-- Export data for assopy_invoice and delete data before migration
.mode insert assopy_invoice
.out /tmp/assopy_invoice.sql
SELECT * FROM assopy_invoice;

-- Export data for conference_event and delete data before migration
.mode insert conference_event
.out /tmp/conference_event.sql
SELECT * FROM conference_event;
END TRANSACTION;

BEGIN TRANSACTION;
DELETE FROM `conference_vototalk` WHERE 1;
DELETE FROM `conference_event` WHERE 1;
DELETE FROM `assopy_invoice` WHERE 1;
END TRANSACTION;
