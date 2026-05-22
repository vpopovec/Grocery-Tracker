#!/usr/bin/env python3
"""Create a user when public registration is disabled."""

import argparse
import getpass

from g_tracker import create_app, db
from g_tracker.models import Person


def main():
    parser = argparse.ArgumentParser(description='Create a Grocery Tracker user')
    parser.add_argument('--username', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--nickname', required=True)
    parser.add_argument('--password', help='If omitted, prompts securely')
    args = parser.parse_args()

    password = args.password or getpass.getpass('Password: ')
    if not password:
        raise SystemExit('Password is required')

    app = create_app()
    with app.app_context():
        if Person.query.filter(
            (Person.username == args.username) | (Person.email == args.email)
        ).first():
            raise SystemExit('Username or email already exists')

        person = Person(
            username=args.username,
            email=args.email,
            name=args.nickname,
        )
        person.set_password(password)
        db.session.add(person)
        db.session.commit()
        print(f'Created user {person.username} (id={person.person_id})')


if __name__ == '__main__':
    main()
