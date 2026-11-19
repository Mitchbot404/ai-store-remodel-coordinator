"""Create isolated synthetic S1-S5 cases; never overwrite existing records."""
import argparse
import getpass
from coordinator.scenarios import build_demo

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('database', help='New SQLite database path')
    args = parser.parse_args()
    password = getpass.getpass('Demo account password (12+ characters): ')
    build_demo(args.database, password)
    print('Created S1-S5. Usernames: ASSOCIATE, SUPPORT, SUPERVISOR, TECHNICAL. Set REMODEL_DB to this path before launching.')
