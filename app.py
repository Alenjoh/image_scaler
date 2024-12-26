from flask import Flask, render_template, request, send_file, jsonify
import io
from main import ImageOptimizer
import os
import logging
from os import environ

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
optimizer = ImageOptimizer()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'heic', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        target_size = int(request.form.get('target_size', 100))  # Default 100KB
        image_data = file.read()
        
        result = optimizer.optimize_image(image_data, target_size)
        
        if result is None:
            return jsonify({'error': 'Optimization failed'}), 400
        
        optimized_data, metadata = result
        
        # Include metadata in response headers
        response = send_file(
            io.BytesIO(optimized_data),
            mimetype='image/jpeg',
            as_attachment=True,
            download_name='optimized.jpg'
        )
        
        response.headers['X-Original-Size'] = str(metadata['original_size_kb'])
        response.headers['X-Final-Size'] = str(metadata['final_size_kb'])
        response.headers['X-Compression-Ratio'] = str(
            round((1 - metadata['final_size_kb'] / metadata['original_size_kb']) * 100)
        )
        
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add error handling
@app.errorhandler(413)
def too_large(e):
    return {"error": "File is too large"}, 413

@app.errorhandler(500)
def server_error(e):
    return {"error": "Internal server error"}, 500

# Add basic security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Add basic logging
logging.basicConfig(level=logging.INFO)

@app.after_request
def after_request(response):
    app.logger.info(f'Path: {request.path} | Status: {response.status_code}')
    return response

# Update your app configuration
app.config['SECRET_KEY'] = environ.get('SECRET_KEY', 'default-secret-key')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(environ.get('PORT', 5000))) 