from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os
import logging
import traceback
from database import db
from routes.quote_routes import quote_routes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

print("Starting Flask application...")

app = Flask(__name__)

# Enable debug mode
app.debug = True

# Set secret key from environment variable or use a default one
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret-key-12345')

try:
    # Register blueprints
    app.register_blueprint(quote_routes)
    print("Successfully registered quote_routes blueprint")
except Exception as e:
    print(f"Error registering blueprint: {str(e)}")
    print(traceback.format_exc())

@app.errorhandler(404)
def not_found_error(error):
    print(f"Page not found: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Server Error: {error}")
    return render_template('500.html'), 500

@app.route('/')
def home():
    logger.info("Accessing home route")
    try:
        logger.info("Attempting to render index template")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        logger.error(traceback.format_exc())
        return str(e), 500

@app.route('/init_test_data')
def init_test_data():
    print("Accessing init test data route")
    try:
        # Add some test suburbs if they don't exist
        test_suburbs = ['Sandton', 'Rosebank', 'Bryanston', 'Morningside']
        for suburb in test_suburbs:
            if not db.suburbs.find_one({'suburb': suburb}):
                db.suburbs.insert_one({'suburb': suburb})
        return 'Test data initialized successfully'
    except Exception as e:
        print(f"Error initializing test data: {str(e)}")
        print(traceback.format_exc())
        return str(e), 500

@app.route('/add_suburb', methods=['POST'])
def add_suburb():
    logger.info("Accessing add suburb route")
    try:
        new_suburb = request.form.get('new_suburb')
        if new_suburb:
            # Check if suburb already exists
            existing = db.suburbs.find_one({'Suburb': new_suburb})
            if not existing:
                db.suburbs.insert_one({'Suburb': new_suburb})
            return new_suburb
        return 'Error', 400
    except Exception as e:
        logger.error(f"Error in add suburb route: {str(e)}")
        logger.error(traceback.format_exc())
        return str(e), 500

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    logger.info("Accessing contact route")
    try:
        # Get all suburbs
        logger.info("Attempting to fetch suburbs from database")
        suburbs = list(db.suburbs.find({}, {"_id": 0, "Suburb": 1}))
        logger.info(f"Found suburbs: {suburbs}")
        
        if request.method == 'POST':
            logger.info("Processing POST request")
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
            logger.info(f"Creating new lead: {new_lead}")
            db.leads.insert_one(new_lead)
            flash('Thank you for your inquiry! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
        
        logger.info("Rendering contact template")
        return render_template('contact.html', suburbs=suburbs)
    except Exception as e:
        logger.error(f"Error in contact route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('500.html'), 500

@app.route('/leads')
def leads():
    print("Accessing leads route")
    try:
        # Get filter parameter from URL
        show_unquoted = request.args.get('show_unquoted', '0') == '1'
        
        # Build query based on filter
        query = {'quoted': False} if show_unquoted else {}
        
        # Get leads with filter applied
        all_leads = list(db.leads.find(query).sort('created_at', -1))
        
        return render_template('leads.html', leads=all_leads, show_unquoted=show_unquoted)
    except Exception as e:
        print(f"Error in leads route: {str(e)}")
        print(traceback.format_exc())
        return str(e), 500

@app.route('/edit_lead/<lead_id>', methods=['GET', 'POST'])
def edit_lead(lead_id):
    print(f"Accessing edit lead route for lead {lead_id}")
    try:
        lead = db.leads.find_one({'_id': ObjectId(lead_id)})
        if not lead:
            flash('Lead not found', 'error')
            return redirect(url_for('leads'))
        
        if request.method == 'POST':
            updated_lead = {
                'first_name': request.form['first_name'],
                'last_name': request.form['last_name'],
                'email': request.form['email'],
                'phone': request.form['phone'],
                'suburb': request.form['suburb'],
                'service': request.form['service'],
                'source': request.form['source'],
                'information': request.form['information'],
                'quoted': lead.get('quoted', False)
            }
            
            db.leads.update_one(
                {'_id': ObjectId(lead_id)},
                {'$set': updated_lead}
            )
            
            flash('Lead updated successfully', 'success')
            return redirect(url_for('leads'))
        
        return render_template('edit_lead.html', lead=lead)
    except Exception as e:
        print(f"Error in edit lead route: {str(e)}")
        print(traceback.format_exc())
        return str(e), 500

@app.route('/convert_to_quote/<lead_id>')
def convert_to_quote(lead_id):
    print(f"Accessing convert to quote route for lead {lead_id}")
    try:
        lead = db.leads.find_one({'_id': ObjectId(lead_id)})
        if not lead:
            return jsonify({'success': False, 'message': 'Lead not found'}), 404
        
        # Update lead status
        db.leads.update_one(
            {'_id': ObjectId(lead_id)},
            {'$set': {'quoted': True}}
        )
        
        # Create new quote
        new_quote = {
            'lead_id': ObjectId(lead_id),
            'Client': f"{lead['first_name']} {lead['last_name']}",
            'Suburb': lead.get('suburb', ''),
            'Service': lead['service'],
            'Source': lead['source'],
            'Cons': 'DR',  # Default value
            'Ref': '',  # Empty reference to start
            'Details': lead.get('information', ''),
            'Date': datetime.utcnow(),
            'Quote Value': 0,  # Default value
            'Sold Value': 0,  # Default value
            'Comments': ''  # Empty comments to start
        }
        
        result = db.quotes.insert_one(new_quote)
        
        if result.inserted_id:
            return jsonify({
                'success': True,
                'message': 'Lead converted to quote successfully',
                'quote_id': str(result.inserted_id)
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create quote'}), 500
            
    except Exception as e:
        print(f"Error converting lead to quote: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    print("Accessing quotes route")
    try:
        if request.method == 'POST':
            new_quote = {
                'Ref': request.form.get('Ref', ''),
                'Cons': request.form.get('Cons'),
                'Source': request.form.get('Source'),
                'Date': datetime.utcnow(),
                'Client': request.form.get('Client'),
                'Suburb': request.form.get('Suburb'),
                'Quote Value': float(request.form.get('Quote Value', 0)),
                'Comments': request.form.get('Comments', ''),
                'Sold Value': float(request.form.get('Sold Value', 0))
            }
            db.quotes.insert_one(new_quote)
            flash('Quote created successfully!', 'success')
            return redirect(url_for('quotes'))

        # Get all quotes and suburbs for the template
        all_quotes = list(db.quotes.find().sort('Date', -1))
        suburbs = list(db.suburbs.find())
        
        return render_template('quotes.html', quotes=all_quotes, suburbs=suburbs)
    except Exception as e:
        print(f"Error in quotes route: {str(e)}")
        print(traceback.format_exc())
        return str(e), 500

@app.route('/api/quotes/<quote_id>', methods=['PUT'])
def update_quote(quote_id):
    print(f"Accessing update quote route for quote {quote_id}")
    try:
        updates = request.json
        print(f"Received updates: {updates}")
        
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
        
        print(f"Update result: {result.modified_count}")
        
        if result.modified_count > 0:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Quote not found'}), 404
            
    except Exception as e:
        print(f"Error updating quote: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/quotes/<quote_id>', methods=['DELETE'])
def delete_quote(quote_id):
    print(f"Accessing delete quote route for quote {quote_id}")
    try:
        print(f"Attempting to delete quote with ID: {quote_id}")
        result = db.quotes.delete_one({'_id': ObjectId(quote_id)})
        print(f"Delete result: {result.deleted_count}")
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Quote deleted successfully'})
        return jsonify({'success': False, 'message': 'Quote not found'}), 404
    except Exception as e:
        print(f"Error deleting quote: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    print(f"Accessing delete lead route for lead {lead_id}")
    try:
        print(f"Attempting to delete lead with ID: {lead_id}")
        result = db.leads.delete_one({'_id': ObjectId(lead_id)})
        print(f"Delete result: {result.deleted_count}")
        if result.deleted_count > 0:
            print('Lead deleted successfully')
            return jsonify({'success': True, 'message': 'Lead deleted successfully'})
        print('Lead not found')
        return jsonify({'success': False, 'message': 'Lead not found'}), 404
    except Exception as e:
        print(f"Error deleting lead: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/debug_quotes')
def debug_quotes():
    print("Accessing debug quotes route")
    quotes = list(db.quotes.find().sort('created_at', -1))
    return jsonify([{k: str(v) if isinstance(v, ObjectId) else v for k, v in quote.items()} for quote in quotes])

@app.route('/test_db')
def test_db():
    try:
        print("Testing database connection")
        # Test MongoDB connection
        db.admin.command('ping')
        print("MongoDB connection successful")
        
        # Try to list collections
        collections = db.list_collection_names()
        print(f"Available collections: {collections}")
        
        return jsonify({
            'status': 'success',
            'message': 'Database connection working',
            'collections': collections
        })
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test')
def test():
    print("Accessing test route")
    try:
        print("Attempting to render test template")
        return render_template('test.html')
    except Exception as e:
        print(f"Error in test route: {str(e)}")
        print(traceback.format_exc())
        return str(e), 500

if __name__ == '__main__':
    print("Starting Flask development server...")
    app.run(debug=True, port=5000)
