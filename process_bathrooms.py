import json
from datetime import datetime
import re

def clean_money_value(value):
    if not value:  # Handle None or empty string
        return 0.0
    # Remove all characters except digits and dots
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def process_bathrooms():
    with open('bathrooms.json', 'r') as file:
        data = json.load(file)
    
    processed_data = []
    for item in data:
        # Convert date string to datetime
        try:
            date = datetime.strptime(item.get('Date', ''), '%d-%m-%Y')
        except ValueError:
            try:
                date = datetime.strptime(item.get('Date', ''), '%Y-%m-%d')
            except ValueError:
                try:
                    date = datetime.strptime(item.get('Date', ''), '%d/%m/%Y')
                except ValueError:
                    print(f"Warning: Could not parse date: {item.get('Date', '')}")
                    date = None
        
        processed_item = {
            'Ref': item.get('Ref', ''),
            'Cons': item.get('Cons', ''),
            'Source': item.get('Source', ''),
            'Client': item.get('Client', ''),
            'Suburb': item.get('Suburb', ''),
            'Quote Value': clean_money_value(item.get('Quote Value')),
            'Sold Value': clean_money_value(item.get('Sold Value')),
            'Comments': item.get('Comments', ''),
            'created_at': date,
            'Date': date
        }
        processed_data.append(processed_item)
    
    # Save processed data to new file
    with open('processed_bathrooms.json', 'w') as file:
        json.dump(processed_data, file, default=str, indent=2)
    
    print(f"\nProcessed {len(processed_data)} records")
    # Print a few examples to verify
    print("\nExample records:")
    for item in processed_data[:3]:
        print(f"Ref: {item['Ref']}")
        print(f"Cons: {item['Cons']}")
        print(f"Source: {item['Source']}")
        print(f"Client: {item['Client']}")
        print(f"Date: {item['Date']}")
        print(f"Quote Value: {item['Quote Value']:,.2f}")
        print(f"Sold Value: {item['Sold Value']:,.2f}")
        print("---")

if __name__ == '__main__':
    process_bathrooms()
