-- test accounts where the user was (manually?) deleted from auth_user --
DELETE FROM `social_auth_usersocialauth` WHERE id=854;
DELETE FROM `conference_attendeeprofile` WHERE user_id=1880;
DELETE FROM `conference_attendeeprofile` WHERE user_id=1896;
DELETE FROM `conference_attendeeprofile` WHERE user_id=2097;
DELETE FROM `p3_p3profile` WHERE profile_id=1880;
DELETE FROM `p3_p3profile` WHERE profile_id=1896;
DELETE FROM `p3_p3profile` WHERE profile_id=2097;
-- votes without talk reference --
DELETE FROM `conference_vototalk` WHERE 1;
-- 2015 invoices without order references --
DELETE FROM `assopy_invoice` WHERE 1;
-- events without references --
DELETE FROM `conference_event` WHERE 1;
