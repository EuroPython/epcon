#!/usr/bin/env python3

""" Fix names in auth_users.

    Usage: ./fix_names data/site/epcon.db

    Uses nameparser package to do the hard work of splitting names into
    first and last name.
 
    Written by Marc-Andre Lemburg, 2019.
 
"""
import sqlite3
import sys
import nameparser

###

def connect(file):

    db = sqlite3.connect(file)
    db.row_factory = sqlite3.Row
    return db

def get_users(db):

    c = db.cursor()
    c.execute('select * from auth_user')
    return c.fetchall()

def fix_names(users):

    """ Fix names in user records.
    
        Yields records (first_name, last_name, id).
    
    """
    for user in users:
        id = user['id']
        first_name = user['first_name'].strip()
        last_name = user['last_name'].strip()
        if not first_name and not last_name:
            # Empty name: skip
            print (f'Skipping empty name in record {id}')
            continue
        elif first_name == last_name:
            full_name = first_name
        elif first_name.endswith(last_name):
            full_name = first_name
        elif not last_name:
            full_name = first_name
        elif not first_name:
            full_name = last_name
        else:
            # In this case, the user has most likely entered the name
            # correctly split, so skip
            full_name = first_name + last_name
            print (f'Skipping already split name: {first_name} / {last_name} ({id})')
            continue
            
        print (f'Working on "{full_name}" ({id})')

        # Handle email addresses
        if '@' in full_name:
            print (f' - fixing email address')
            # Remove domain part
            e_name = full_name[:full_name.find('@')]
            if '+' in e_name:
                # Remove alias
                e_name = e_name[:e_name.find('+')]
            # Try to split name parts
            e_name = e_name.replace('.', ' ')
            e_name = e_name.replace('_', ' ')
            e_name = e_name.strip()
            if len(e_name) < 4:
                # Probably just initials: leave email as is
                pass
            else:
                full_name = e_name
        
        # Parse name
        name = nameparser.HumanName(full_name)
        name.capitalize()
        first_name = name.first
        last_name = name.last
        print (f' - splitting name into: {first_name} / {last_name} ({id})')
        yield (first_name, last_name, id)

def update_users(db, user_data):

    c = db.cursor()
    c.executemany('update auth_user set first_name=?, last_name=? where id=?', 
                  user_data)
    db.commit()

###

if __name__ == '__main__':
    db = connect(sys.argv[1])
    users = get_users(db)
    user_data = fix_names(users)
    update_users(db, user_data)
