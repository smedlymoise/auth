import urllib.parse 
import requests 
import os 
from datetime import datetime, timedelta  
from flask import Flask, redirect, request, jsonify, session, render_template  

app = Flask(__name__)  # Creating a Flask application

# Load environment variables from .env file
# load_dotenv()

# Access environment variables
app.secret_key = os.getenv("key_secret")
CLIENT_ID = os.getenv("id_client")  
CLIENT_SECRET = os.getenv("secret_client")  
REDIRECT_URI = os.getenv("redirect") 
Auth_URL = os.getenv("URL_A")  
TOKEN_URL = os.getenv("URL_TOK")  
API_BASE_URL = os.getenv("BASE_URL_API")  

@app.route('/')  # Route for the home page
def index():
    return "Welcome <a href='/login'> Login with Spotify</a>"  # Displaying a welcome message with a link to login with Spotify

@app.route('/login')  # Route for initiating the login process
def login():
    scope = 'user-read-private'  # Scope required for accessing private user data
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True,  # Option to show dialog to prevent user from logging in again
    }

    auth_url = f"{Auth_URL}?{urllib.parse.urlencode(params)}"  # Constructing the authorization URL

    return redirect(auth_url)  # Redirecting the user to the authorization URL

@app.route('/callback')  # Route for handling callback after authentication
def callback():
    if 'error' in request.args:  # Handling errors from the callback
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:  # If authorization code is received
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        response = requests.post(TOKEN_URL, data=req_body)  # Sending a POST request to exchange code for access tokens

        token_info = response.json()  # Parsing the response JSON

        session['access_token'] = token_info['access_token']  # Storing access token in session
        session['refresh_token'] = token_info['refresh_token']  # Storing refresh token in session
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']  # Storing expiration time in session

        return redirect('/artist_search')  # Redirecting to artist search page

@app.route('/artist_search', methods=['GET', 'POST'])  # Route for searching artists
def get_artist():
    if 'access_token' not in session:  # Checking if access token is present in session
        return redirect('/login')  # Redirecting to login if access token is missing

    if datetime.now().timestamp() > session['expires_at']:  # Checking if access token has expired
        return redirect('/refresh-token')  # Redirecting to refresh token endpoint if token has expired

    if request.method == 'POST':  # Handling POST request for artist search
        artist_name = request.form.get('artist_name')  # Getting artist name from form data
        if not artist_name:  # If artist name is missing
            return jsonify({"error": "Artist name is required"}), 400  # Returning an error message
        
        headers = {
            'Authorization': f"Bearer {session['access_token']}"  # Constructing authorization header with access token
        }

        params = {
            'q': artist_name,
            'type': 'artist',
            'limit': 1
        }
        search_response = requests.get(API_BASE_URL + 'search', headers=headers, params=params)  # Sending request to search for artist
        search_results = search_response.json()  # Parsing search results JSON

        if 'artists' in search_results and 'items' in search_results['artists'] and len(search_results['artists']['items']) > 0:
            artist_id = search_results['artists']['items'][0]['id']  # Getting artist ID
            top_tracks_response = requests.get(API_BASE_URL + f'artists/{artist_id}/top-tracks', headers=headers, params={'country': 'US'})  # Getting top tracks for artist
            top_tracks = top_tracks_response.json()  # Parsing top tracks JSON

            top_tracks_info = []
            if 'tracks' in top_tracks:
                for track_info in top_tracks['tracks'][:12]:  # Limiting to top 12 tracks
                    track_name = track_info['name']
                    album_name = track_info['album']['name']
                    album_image = track_info['album']['images'][0]['url']  # Getting the first image 
                    top_tracks_info.append({
                        "track": track_name,
                        "album": album_name,
                        "album_image": album_image
                    })

                return render_template('artist_search.html', artist=artist_name, top_tracks=top_tracks_info)  # Rendering template with artist info and top tracks
            else:
                return jsonify({"error": "No tracks found for the artist"}), 404  # Returning error if no tracks found
        else:
            return jsonify({"error": "Artist not found"}), 404  # Returning error if artist not found

    return render_template('artist_search_form.html')  # Rendering artist search form template

@app.route('/refresh-token')  # Route for refreshing access token
def refresh_token():
    if 'refresh_token' not in session:  # Checking if refresh token is present in session
        return redirect('/login')  # Redirecting to login if refresh token is missing

    if datetime.now().timestamp() > session['expires_at']:  # Checking if access token has expired
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)  # Sending request to refresh access token
        new_token_info = response.json()  # Parsing response JSON

        session['access_token'] = new_token_info['access_token']  # Updating access token in session
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']  # Updating expiration time in session

        return redirect('/artist_search')  # Redirecting to artist search page

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
