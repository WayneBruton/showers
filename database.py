import os
import logging
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_database():
    try:
        logger.info("Getting MongoDB URI from environment...")
        mongodb_uri = os.getenv('MONGODB_URI', '').strip('"\'')  # Remove any quotes
        
        if not mongodb_uri:
            logger.error("MONGODB_URI environment variable not set!")
            raise ValueError("MONGODB_URI environment variable not set!")
        
        logger.info("Attempting to connect to MongoDB...")
        client = MongoClient(mongodb_uri, tlsCAFile=certifi.where())
        
        # Test the connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
        
        # Explicitly get the 'shower' database
        db = client.shower  # Use dot notation instead of dictionary access
        logger.info(f"Using database: {db.name}")
        
        return db
        
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

# Get database
db = get_database()
