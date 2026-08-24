from flask import Flask, request, jsonify

# Memanggil fungsi dari file animein_scraper.py yang ada di folder api
from api.animein_scraper import ep_home, ep_explore, ep_episode_list, ep_stream

app = Flask(__name__)

@app.route('/api/home', methods=['GET'])
def home():
    try:
        # Mengambil data beranda
        data = ep_home(day="1", limit="20")
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 0))
    try:
        # Mengambil data pencarian
        data = ep_explore(page=page, sort="views", keyword=keyword)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/episodes/<int:movie_id>', methods=['GET'])
def episodes(movie_id):
    page = int(request.args.get('page', 0))
    try:
        # Mengambil daftar episode
        data = ep_episode_list(movie_id, page=page)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/stream/<int:episode_id>', methods=['GET'])
def stream(episode_id):
    try:
        # Mengambil link video MP4
        data = ep_stream(episode_id)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})
      
