from flask import Flask, render_template, jsonify
from scraper import TwitterTrendsScraper
import json
from bson import json_util

app = Flask(__name__)
scraper = TwitterTrendsScraper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-scraper')
def run_scraper():
    try:
        record = scraper.get_trending_topics()
        return jsonify({
            'success': True,
            'data': json.loads(json_util.dumps(record))
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/latest-record')
def get_latest_record():
    record = scraper.get_latest_record()
    return jsonify({
        'success': True,
        'data': json.loads(json_util.dumps(record))
    })

if __name__ == '__main__':
    app.run(debug=True)