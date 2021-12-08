import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///blog.db')
DATABASE_URL1 = os.getenv('DATABASE_URL1', 'sqlite:///blog.db')

EMAIL = os.getenv('SENDER_EMAIL')
PASSWORD = os.getenv('MY_PASSWORD')
