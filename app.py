from __future__ import print_function
import binascii
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import Flask-CORS
import requests
from io import BytesIO
from PIL import Image
import numpy as np
import scipy.cluster
from scipy.cluster.hierarchy import linkage, fcluster

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Number of clusters for the initial k-means (we use more than we ultimately return)
NUM_INITIAL_CLUSTERS = 10
# Threshold for grouping similar clusters (in RGB space; you can adjust this if needed)
SIMILARITY_THRESHOLD = 30.0

def rgb_to_hex(rgb):
    """Convert an (R,G,B) array to hex string."""
    return '#' + ''.join(format(int(round(c)), '02x') for c in rgb)

@app.route('/dominant-color', methods=['POST'])
def dominant_color():
    data = request.get_json()
    if not data or 'photoUrl' not in data:
        return jsonify({'error': 'Please provide a photoUrl in the request body'}), 400

    photo_url = data['photoUrl']
    
    try:
        # Download and open the image
        response = requests.get(photo_url)
        response.raise_for_status()  # Raise error for bad responses
        image_data = BytesIO(response.content)
        im = Image.open(image_data)
        im = im.convert('RGB')
        im = im.resize((150, 150))  # Resize to speed up processing

        # Convert the image to a numpy array of pixels
        ar = np.asarray(im)
        shape = ar.shape  # (height, width, channels)
        # Use np.prod instead of np.product for compatibility
        pixels = ar.reshape(np.prod(shape[:2]), shape[2]).astype(float)
        
        # Run k-means clustering on the pixels using NUM_INITIAL_CLUSTERS clusters
        centers, _ = scipy.cluster.vq.kmeans(pixels, NUM_INITIAL_CLUSTERS)
        assignments, _ = scipy.cluster.vq.vq(pixels, centers)
        # Count the number of pixels in each cluster
        counts, _ = np.histogram(assignments, bins=np.arange(NUM_INITIAL_CLUSTERS+1))
        
        # Group similar clusters together using hierarchical clustering on the centers
        Z = linkage(centers, method='ward')
        # fcluster returns group labels; clusters within SIMILARITY_THRESHOLD are merged
        group_labels = fcluster(Z, t=SIMILARITY_THRESHOLD, criterion='distance')
        
        # Merge clusters by group label, computing a weighted average centroid per group.
        merged_groups = {}
        for i, label in enumerate(group_labels):
            if label not in merged_groups:
                merged_groups[label] = {"sum": np.zeros(3), "count": 0}
            # Weight the center by its pixel count
            merged_groups[label]["sum"] += centers[i] * counts[i]
            merged_groups[label]["count"] += counts[i]
        
        # Compute the final merged centroid for each group and create a list with (centroid, count)
        merged = []
        for label, group in merged_groups.items():
            if group["count"] > 0:
                centroid = group["sum"] / group["count"]
                merged.append((centroid, group["count"]))
        
        # Sort the merged groups by the number of pixels (most prevalent first)
        merged.sort(key=lambda x: x[1], reverse=True)
        
        # Take the top 5 colors from the merged palette
        top5 = merged[:5]
        palette = [rgb_to_hex(c) for c, count in top5]
        
        # The dominant color is the first one in the sorted palette
        dominant = palette[0] if palette else None
        
        return jsonify({
            "dominantColor": dominant,
            "palette": palette
        })
    except Exception as e:
        print("Error processing image:", e)
        return jsonify({'error': 'Error processing the image.'}), 500

if __name__ == '__main__':
    app.run(port=3048)
