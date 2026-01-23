from flask import Flask, jsonify, render_template, request
import random
from datetime import datetime, timedelta
import requests
import json
import os

app = Flask(__name__)

# Path to historical data storage
HISTORICAL_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'historical_snapshots.json')

# Mock candidate data
CANDIDATES = [
    {"id": 1, "name": "Maria Garcia", "party_role": "State Rep", "color": "#FF6B6B"},
    {"id": 2, "name": "James Wilson", "party_role": "Community Organizer", "color": "#4ECDC4"},
    {"id": 3, "name": "Dr. Sarah Ahmed", "party_role": "Physician", "color": "#45B7D1"},
    {"id": 4, "name": "Tom Mueller", "party_role": "Labor Leader", "color": "#FFA07A"},
    {"id": 5, "name": "Angela Chen", "party_role": "Tech Entrepreneur", "color": "#98D8C8"},
    {"id": 6, "name": "Robert Jackson", "party_role": "Former Alderman", "color": "#F7DC6F"},
]

# Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/odds')
def odds():
    return render_template('odds.html')

@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/markets')
def markets():
    return render_template('markets.html')

@app.route('/fundraising')
def fundraising():
    return render_template('fundraising.html')

# API Endpoints
@app.route('/api/forecast')
def get_forecast():
    """Generate mock forecast data"""
    random.seed(42)
    base_odds = [28, 22, 18, 16, 10, 6]
    odds = [max(1, o + random.randint(-3, 3)) for o in base_odds]
    total = sum(odds)
    odds = [round(100 * o / total) for o in odds]

    candidates = []
    for i, candidate in enumerate(CANDIDATES):
        candidates.append({
            **candidate,
            "probability": odds[i],
            "trend": random.choice(["up", "down", "stable"]),
            "polling_avg": round(odds[i] + random.uniform(-2, 2), 1),
            "change": random.randint(-5, 5),
            "last_update": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat()
        })

    return jsonify({
        "candidates": candidates,
        "last_updated": datetime.now().isoformat(),
        "primary_date": "2026-03-17"
    })

@app.route('/api/timeline')
def get_timeline():
    """Generate mock polling trend data"""
    timeline = []
    start_date = datetime.now() - timedelta(days=90)

    for day in range(0, 91, 7):
        current_date = start_date + timedelta(days=day)
        day_data = {
            "date": current_date.strftime("%Y-%m-%d"),
            "candidates": {}
        }

        base = [25, 22, 18, 15, 12, 8]
        for i, candidate in enumerate(CANDIDATES):
            variance = random.randint(-4, 4)
            day_data["candidates"][candidate["name"]] = max(1, base[i] + variance)

        timeline.append(day_data)

    return jsonify(timeline)

@app.route('/api/manifold')
def get_manifold():
    """Proxy Manifold Markets API to avoid CORS"""
    try:
        response = requests.get('https://api.manifold.markets/v0/slug/who-will-win-the-democratic-primary-RZdcps6dL9')
        response.raise_for_status()
        result = jsonify(response.json())
        result.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        result.headers['Pragma'] = 'no-cache'
        result.headers['Expires'] = '0'
        return result
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/kalshi')
def get_kalshi():
    """Proxy Kalshi API to avoid CORS"""
    try:
        response = requests.get('https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXIL9D&status=open')
        response.raise_for_status()
        result = jsonify(response.json())
        result.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        result.headers['Pragma'] = 'no-cache'
        result.headers['Expires'] = '0'
        return result
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manifold/history')
def get_manifold_history():
    """Get Manifold market history for chart"""
    try:
        # Get the market first to get the ID
        market_response = requests.get('https://api.manifold.markets/v0/slug/who-will-win-the-democratic-primary-RZdcps6dL9')
        market_response.raise_for_status()
        market = market_response.json()
        market_id = market.get('id')

        # Get bets for this market
        bets_response = requests.get(f'https://api.manifold.markets/v0/bets?contractId={market_id}&limit=1000')
        bets_response.raise_for_status()
        bets = bets_response.json()

        return jsonify({
            "market": market,
            "bets": bets
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/kalshi/history/<ticker>')
def get_kalshi_history(ticker):
    """Get Kalshi market history for a specific ticker"""
    try:
        response = requests.get(f'https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}/history?limit=1000')
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/snapshot', methods=['POST'])
def save_snapshot():
    """Save a historical snapshot of aggregated probabilities"""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(HISTORICAL_DATA_PATH), exist_ok=True)

        # Load existing snapshots
        if os.path.exists(HISTORICAL_DATA_PATH):
            with open(HISTORICAL_DATA_PATH, 'r') as f:
                snapshots = json.load(f)
        else:
            snapshots = []

        # Get new snapshot from request
        new_snapshot = request.json
        new_snapshot['timestamp'] = datetime.now().isoformat()

        # Append new snapshot
        snapshots.append(new_snapshot)

        # Save back to file
        with open(HISTORICAL_DATA_PATH, 'w') as f:
            json.dump(snapshots, f, indent=2)

        return jsonify({"success": True, "total_snapshots": len(snapshots)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/snapshots')
def get_snapshots():
    """Retrieve historical snapshots for charting"""
    try:
        if not os.path.exists(HISTORICAL_DATA_PATH):
            return jsonify([])

        with open(HISTORICAL_DATA_PATH, 'r') as f:
            snapshots = json.load(f)

        return jsonify(snapshots)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use debug mode only for local development
    import os
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
