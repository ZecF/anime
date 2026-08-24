from flask import Flask, request, jsonify, Response
import urllib.request

# Memanggil fungsi dari file animein_scraper.py yang ada di folder api
from api.animein_scraper import ep_home, ep_explore, ep_episode_list, ep_stream

app = Flask(__name__)

# --- TAMBAHAN BARU: PROXY GAMBAR ANTI BLOKIR ---
@app.route('/api/image', methods=['GET'])
def proxy_image():
    img_url = request.args.get('url')
    if not img_url:
        return "URL tidak ditemukan", 400
        
    # Menyamar sebagai website resmi AnimeIn
    req = urllib.request.Request(img_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        "Referer": "https://www.animeinweb.com/"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            # Mengirimkan gambar utuh ke HTML
            return Response(r.read(), mimetype=r.headers.get_content_type())
    except Exception as e:
        return str(e), 500
# -----------------------------------------------

@app.route('/api/home', methods=['GET'])
def home():
    try:
        data = ep_home(day="1", limit="20")
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 0))
    try:
        data = ep_explore(page=page, sort="views", keyword=keyword)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/episodes/<int:movie_id>', methods=['GET'])
def episodes(movie_id):
    page = int(request.args.get('page', 0))
    try:
        data = ep_episode_list(movie_id, page=page)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})

@app.route('/api/stream/<int:episode_id>', methods=['GET'])
def stream(episode_id):
    try:
        data = ep_stream(episode_id)
        return jsonify({"status": 200, "data": data})
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)})
      
