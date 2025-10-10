from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv()
#
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DB_URL = os.environ.get('DB_URL')
# SECRET_KEY_PUBLIC = os.environ.get('SECRET_KEY_PUBLIC')
# SECRET_KEY_PRIVATE = os.environ.get('SECRET_KEY_PRIVATE')
# SECRET_KEY_HS256 = os.environ.get('SECRET_KEY_HS256')
# SECRET_KEY_RESET = os.environ.get('SECRET_KEY_RESET')
# SECRET_KEY_VERIFICATION = os.environ.get('SECRET_KEY_VERIFICATION')

if __name__ == '__main__':
    print(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f'{BASE_DIR=}')

    print(f'DB_HOST: {DB_HOST}\n',
          f'DB_PORT: {DB_PORT}\n',
          f'DB_NAME: {DB_NAME}\n',
          f'DB_USER: {DB_USER}\n',
          f'DB_PASS: {DB_PASS}\n',
          f'DB_URL: {DB_URL}\n')