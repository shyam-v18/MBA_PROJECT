import os
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from mba_engine import MBAEngine

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

engine = None  # Will hold the MBAEngine instance after analysis

# ------------------- Frontend -------------------
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

# ------------------- APIs -------------------
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload CSV file to the data folder."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': 'File uploaded successfully', 'filename': filename})

@app.route('/api/analyze', methods=['POST'])
def run_analysis():
    """Run the MBA algorithm with given parameters."""
    global engine
    data = request.json
    filename = data.get('filename')
    min_support = float(data.get('min_support', 0.02))
    min_confidence = float(data.get('min_confidence', 0.1))
    min_freq = int(data.get('min_freq', 20))

    if not filename:
        return jsonify({'error': 'Filename is required'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found. Please upload first.'}), 404

    try:
        # Initialize and run the engine
        engine = MBAEngine(filepath, output_dir=app.config['OUTPUT_FOLDER'])
        engine.run(min_support=min_support, min_confidence=min_confidence, min_freq=min_freq)
        
        # Get summary stats
        stats = {
            'total_transactions': engine.basket.shape[0],
            'total_products': engine.basket.shape[1],
            'frequent_itemsets': len(engine.frequent_itemsets),
            'total_rules': len(engine.rules),
            'strong_rules': len(engine.strong_rules)
        }
        
        # Generate plot filenames
        plots = [
            'top_items.png',
            'support_dist.png',
            'top_rules_lift.png',
            'support_vs_confidence.png',
            'confidence_vs_lift.png'
        ]
        # Make sure plots exist
        for p in plots:
            if not os.path.exists(os.path.join(app.config['OUTPUT_FOLDER'], p)):
                return jsonify({'error': f'Plot {p} not generated'}), 500

        return jsonify({
            'message': 'Analysis complete',
            'stats': stats,
            'plots': plots
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-items', methods=['GET'])
def get_top_items():
    """Return top 20 frequent items."""
    global engine
    if not engine or engine.frequent_itemsets is None:
        return jsonify({'error': 'No analysis run yet. Please run /api/analyze first.'}), 400
    top = engine.frequent_itemsets.head(20).copy()
    top['items'] = top['itemsets'].apply(lambda x: ', '.join(sorted(list(x))))
    return jsonify(top[['items', 'support']].to_dict(orient='records'))

@app.route('/api/top-rules', methods=['GET'])
def get_top_rules():
    """Return top 20 rules by lift."""
    global engine
    if not engine or engine.rules is None:
        return jsonify({'error': 'No analysis run yet.'}), 400
    top = engine.rules.nlargest(20, 'lift').copy()
    top['antecedents'] = top['antecedents'].apply(lambda x: ', '.join(sorted(list(x))))
    top['consequents'] = top['consequents'].apply(lambda x: ', '.join(sorted(list(x))))
    return jsonify(top[['antecedents', 'consequents', 'support', 'confidence', 'lift']].to_dict(orient='records'))

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """Get recommendations for a given product."""
    global engine
    if not engine:
        return jsonify({'error': 'No analysis run yet.'}), 400
    data = request.json
    product = data.get('product', '').strip().upper()
    if not product:
        return jsonify({'error': 'Product name is required'}), 400
    recs = engine.recommend(product, top_n=5)
    return jsonify(recs.to_dict(orient='records'))

@app.route('/api/plots/<filename>')
def serve_plot(filename):
    """Serve generated plot images."""
    safe_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, mimetype='image/png')
    return jsonify({'error': 'Plot not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)