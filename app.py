import urllib.parse
import requests
import os
from datetime import datetime, timedelta
from flask import Flask, redirect, request, jsonify, session, render_template

app = Flask(__name__)

# Access environment variables
app.secret_key = os.getenv("key_secret")
CLIENT_ID = os.getenv("id_client")
CLIENT_SECRET = os.getenv("secret_client")
REDIRECT_URI = os.getenv("redirect")
Auth_URL = os.getenv("URL_A")
TOKEN_URL = os.getenv("URL_TOK")
API_BASE_URL = os.getenv("BASE_URL_API")

@app.route('/')
def index():
    return "Welcome <a href='/login'> Login with Spotify</a>"

@app.route('/login')
def login():
    scope = 'user-read-private'
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True,  # so user doesn't have to login again
    }

    auth_url = f"{Auth_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        response = requests.post(TOKEN_URL, data=req_body)

        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return redirect('/artist_search')

@app.route('/artist_search', methods=['GET', 'POST'])
def get_artist():
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    if request.method == 'POST':
        artist_name = request.form.get('artist_name')
        if not artist_name:
            return jsonify({"error": "Artist name is required"}), 400

        headers = {
            'Authorization': f"Bearer {session['access_token']}"
        }

        params = {
            'q': artist_name,
            'type': 'artist',
            'limit': 1
        }
        search_response = requests.get(API_BASE_URL + 'search', headers=headers, params=params)
        search_results = search_response.json()

        if 'artists' in search_results and 'items' in search_results['artists'] and len(search_results['artists']['items']) > 0:
            artist_id = search_results['artists']['items'][0]['id']
            top_tracks_response = requests.get(API_BASE_URL + f'artists/{artist_id}/top-tracks', headers=headers, params={'country': 'US'})
            top_tracks = top_tracks_response.json()

            top_tracks_info = []
            if 'tracks' in top_tracks:
                for track_info in top_tracks['tracks'][:12]:  # Limit to top 4 tracks
                    track_name = track_info['name']
                    album_name = track_info['album']['name']
                    album_image = track_info['album']['images'][0]['url']  # Getting the first image 
                    top_tracks_info.append({
                        "track": track_name,
                        "album": album_name,
                        "album_image": album_image
                    })

                return render_template('artist_search.html', artist=artist_name, top_tracks=top_tracks_info)
            else:
                return jsonify({"error": "No tracks found for the artist"}), 404
        else:
            return jsonify({"error": "Artist not found"}), 404

    return render_template('artist_search_form.html')

@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/artist_search')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
