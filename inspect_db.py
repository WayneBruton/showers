from pymongo import MongoClient
from pprint import pprint
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGODB_URI')
print(f"MongoDB URI (masked): {mongo_uri[:10]}...{mongo_uri[-10:]}")

client = MongoClient(mongo_uri)
db = client.showerdesignz

# List all collections
print("\nAll collections in database:")
collections = db.list_collection_names()
for collection in collections:
    count = db[collection].count_documents({})
    print(f"{collection}: {count} documents")

# Get all quotes
quotes = list(db.quotes.find())

print("\nFirst 3 quotes from database:")
for i, quote in enumerate(quotes[:3]):
    print(f"\nQuote {i+1}:")
    pprint(quote)

print("\nField names in first quote:")
if quotes:
    print(list(quotes[0].keys()))

# Count documents
print(f"\nTotal number of quotes: {len(quotes)}")
