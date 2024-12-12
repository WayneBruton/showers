from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.shower  # Use the 'shower' database

# Routes
@app.route('/init_test_data')
def init_test_data():
    # Add some test suburbs if they don't exist
    test_suburbs = ['Sandton', 'Rosebank', 'Bryanston', 'Morningside']
    for suburb in test_suburbs:
        if not db.suburbs.find_one({'suburb': suburb}):
            db.suburbs.insert_one({'suburb': suburb})
    return 'Test data initialized'

@app.route('/')
def home():
    return redirect(url_for('contact'))

@app.route('/add_suburb', methods=['POST'])
def add_suburb():
    new_suburb = request.form.get('new_suburb')
    if new_suburb:
        # Check if suburb already exists
        existing = db.suburbs.find_one({'suburb': new_suburb})
        if not existing:
            db.suburbs.insert_one({'suburb': new_suburb})
        return new_suburb
    return 'Error', 400

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    suburbs = list(db.suburbs.find({},{ "_id": 0, "Suburb": 1}))
    # print(len(suburbs))  # Debug print
    # for suburb in suburbs:
    #     print(suburb)
    print("Found suburbs:", suburbs)  # Debug print
    if request.method == 'POST':
        new_lead = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'suburb': request.form['suburb'],
            'service': request.form['service'],
            'source': request.form['source'],
            'information': request.form['information'],
            'quoted': False,
            'created_at': datetime.utcnow()
        }
        db.leads.insert_one(new_lead)
        flash('Thank you for your inquiry! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', suburbs=suburbs)

@app.route('/leads')
def leads():
    # Get filter parameter from URL
    show_unquoted = request.args.get('show_unquoted', '0') == '1'
    
    # Build query based on filter
    query = {'quoted': False} if show_unquoted else {}
    
    # Get leads with filter applied
    all_leads = list(db.leads.find(query).sort('created_at', -1))
    
    return render_template('leads.html', leads=all_leads, show_unquoted=show_unquoted)

@app.route('/convert_to_quote/<lead_id>')
def convert_to_quote(lead_id):
    lead = db.leads.find_one({'_id': ObjectId(lead_id)})
    if lead:
        # Update lead status
        db.leads.update_one(
            {'_id': ObjectId(lead_id)},
            {'$set': {'quoted': True}}
        )
        
        # Create new quote
        new_quote = {
            'lead_id': ObjectId(lead_id),
            'first_name': lead['first_name'],
            'last_name': lead['last_name'],
            'email': lead['email'],
            'phone': lead['phone'],
            'suburb': lead.get('suburb', ''),
            'service': lead['service'],
            'source': lead['source'],  # Changed from lead.get('source', '') to ensure we get the source
            'cons': 'DR',  # Default value
            'ref': '',  # Empty reference to start
            'details': lead.get('information', ''),
            'created_at': datetime.utcnow()
        }
        print("Creating quote with source:", lead['source'])  # Debug print
        db.quotes.insert_one(new_quote)
    return redirect(url_for('quotes'))

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    suburbs = list(db.suburbs.find({}, {"_id": 0, "Suburb": 1}).sort('Suburb', 1))
    if request.method == 'POST':
        # Split client name into first and last name
        client_name = request.form['client_name'].split(' ', 1)
        first_name = client_name[0]
        last_name = client_name[1] if len(client_name) > 1 else ''

        new_quote = {
            'ref': request.form.get('ref', ''),
            'cons': request.form['cons'],
            'source': request.form['source'],
            'first_name': first_name,
            'last_name': last_name,
            'suburb': request.form['suburb'],
            'amount': float(request.form['amount']) if request.form['amount'] else None,
            'comments': request.form.get('comments', ''),
            'sold_value': float(request.form['sold_value']) if request.form['sold_value'] else None,
            'created_at': datetime.utcnow()
        }
        db.quotes.insert_one(new_quote)
        flash('Quote created successfully!', 'success')
        return redirect(url_for('quotes'))
    
    all_quotes = list(db.quotes.find().sort('created_at', -1))
    return render_template('quotes.html', quotes=all_quotes, suburbs=suburbs)

@app.route('/api/quotes/<quote_id>', methods=['PUT'])
def update_quote(quote_id):
    try:
        updates = request.json
        print("Received updates:", updates)  # Debug print
        
        # Convert string values to appropriate types
        if 'amount' in updates:
            updates['amount'] = float(updates['amount'])
        if 'sold_value' in updates:
            updates['sold_value'] = float(updates['sold_value'])
            
        # Update the quote in the database
        result = db.quotes.update_one(
            {'_id': ObjectId(quote_id)},
            {'$set': updates}
        )
        
        print("Update result:", result.modified_count)  # Debug print
        
        if result.modified_count > 0:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Quote not found'}), 404
            
    except Exception as e:
        print("Error updating quote:", str(e))  # Debug print
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
