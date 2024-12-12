from flask import jsonify, request
from bson import ObjectId
from app import app, db

@app.route('/api/quotes/<quote_id>', methods=['PUT'])
def update_quote(quote_id):
    try:
        updates = request.json
        print("Received updates:", updates)
        
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
        
        print("Update result:", result.modified_count)
        
        if result.modified_count > 0:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Quote not found'}), 404
            
    except Exception as e:
        print("Error updating quote:", str(e))
        return jsonify({'error': str(e)}), 500
