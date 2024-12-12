from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os
from database import db
from routes.quote_routes import quote_routes

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.register_blueprint(quote_routes)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

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
            'Client': lead['first_name'] + ' ' + lead['last_name'],
            'Suburb': lead.get('suburb', ''),
            'Service': lead['service'],
            'Source': lead['source'],  # Changed from lead.get('source', '') to ensure we get the source
            'Cons': 'DR',  # Default value
            'Ref': '',  # Empty reference to start
            'Details': lead.get('information', ''),
            'created_at': datetime.utcnow()
        }
        print("Creating quote with source:", lead['source'])  # Debug print
        db.quotes.insert_one(new_quote)
    return redirect(url_for('quotes'))

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    suburbs = list(db.suburbs.find({}, {"_id": 0, "Suburb": 1}).sort('Suburb', 1))
    if request.method == 'POST':
        new_quote = {
            'ref': request.form.get('ref', ''),
            'cons': request.form['cons'],
            'source': request.form['source'],
            'client': request.form['client_name'],
            'suburb': request.form['suburb'],
            'quote_value': float(request.form['amount']) if request.form['amount'] else None,
            'comments': request.form.get('comments', ''),
            'sold_value': float(request.form['sold_value']) if request.form['sold_value'] else None,
            'date': request.form.get('date', datetime.utcnow().strftime('%Y-%m-%d')),
            'created_at': datetime.utcnow()
        }
        db.quotes.insert_one(new_quote)
        flash('Quote created successfully!', 'success')
        return redirect(url_for('quotes'))
    
    # Fetch quotes and print debug info
    all_quotes = list(db.quotes.find().sort('created_at', -1))
    print("\nDebug: First quote from MongoDB:")
    if all_quotes:
        print(f"Keys in first quote: {all_quotes[0].keys()}")
        print(f"Full first quote: {all_quotes[0]}")
    
    # Convert date strings to datetime objects
    for quote in all_quotes:
        if isinstance(quote.get('created_at'), str):
            try:
                quote['created_at'] = datetime.strptime(quote['created_at'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                quote['created_at'] = datetime.utcnow()
        
        # Ensure numeric fields are floats
        if 'quote_value' in quote and quote['quote_value'] is not None:
            try:
                quote['quote_value'] = float(quote['quote_value'])
            except (ValueError, TypeError):
                quote['quote_value'] = 0.0
                
        if 'sold_value' in quote and quote['sold_value'] is not None:
            try:
                quote['sold_value'] = float(quote['sold_value'])
            except (ValueError, TypeError):
                quote['sold_value'] = 0.0
    
    return render_template('quotes.html', quotes=all_quotes, suburbs=suburbs)

@app.route('/api/quotes/<quote_id>', methods=['PUT'])
def update_quote(quote_id):
    try:
        updates = request.json
        print("Received updates:", updates)  # Debug print
        
        # Convert string values to appropriate types
        if 'Quote Value' in updates:
            updates['Quote Value'] = float(updates['Quote Value'])
        if 'Sold Value' in updates:
            updates['Sold Value'] = float(updates['Sold Value'])
            
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

@app.route('/api/quotes/<quote_id>', methods=['DELETE'])
def delete_quote(quote_id):
    try:
        print(f"Attempting to delete quote with ID: {quote_id}")  # Debug log
        result = db.quotes.delete_one({'_id': ObjectId(quote_id)})
        print(f"Delete result: {result.deleted_count}")  # Debug log
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Quote deleted successfully'})
        return jsonify({'success': False, 'message': 'Quote not found'}), 404
    except Exception as e:
        print("Error deleting quote:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    try:
        result = db.leads.delete_one({'_id': ObjectId(lead_id)})
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Lead deleted successfully'})
        return jsonify({'success': False, 'message': 'Lead not found'}), 404
    except Exception as e:
        print("Error deleting lead:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/debug_quotes')
def debug_quotes():
    quotes = list(db.quotes.find().sort('created_at', -1))
    return jsonify([{k: str(v) if isinstance(v, ObjectId) else v for k, v in quote.items()} for quote in quotes])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
