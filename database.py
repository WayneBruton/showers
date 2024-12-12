from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment variable
uri = os.getenv('MONGODB_URI')

# Add database name to URI if not present
if '?' in uri:
    uri = uri.replace('/?', '/shower?')
else:
    uri = uri + '/shower'

# Create MongoDB client with server API version
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.get_database()

# Test the connection
try:
    # Send a ping to confirm a successful connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    
    # Print database info
    print(f"Current database: {db.name}")
    print(f"Available collections: {db.list_collection_names()}")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
