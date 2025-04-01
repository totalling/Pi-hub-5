#!/usr/bin/env python3
"""
Spotify Mini Player
A lightweight Flask app to display currently playing Spotify music
"""

from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import os
import time
import uuid
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import psutil
import shutil
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spotify-mini-secret-key'

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/spotify/callback')
SPOTIFY_SCOPE = "user-read-playback-state user-read-recently-played user-read-currently-playing"
SPOTIFY_AVAILABLE = bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)

if SPOTIFY_AVAILABLE:
    try:
        sp_oauth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            cache_path=".spotify_cache"
        )
        print(f"Spotify OAuth configured with redirect URI: {SPOTIFY_REDIRECT_URI}")
    except Exception as e:
        print(f"Error initializing Spotify OAuth: {e}")
        sp_oauth = None
        SPOTIFY_AVAILABLE = False

@app.route('/')
def index():
    """Render the mini player page"""
    spotify_connected = bool(session.get('spotify_token_info'))
    return render_template('index.html', 
                          spotify_available=SPOTIFY_AVAILABLE,
                          spotify_connected=spotify_connected)

@app.route('/spotify/login')
def spotify_login():
    """Initiate the Spotify OAuth flow"""
    if not SPOTIFY_AVAILABLE:
        return jsonify({'error': 'Spotify credentials not configured'}), 500
    
    state = str(uuid.uuid4())
    session['spotify_auth_state'] = state
    
    auth_url = sp_oauth.get_authorize_url(state=state)
    return redirect(auth_url)

@app.route('/spotify/callback')
def spotify_callback():
    """Handle the Spotify OAuth callback"""
    if not SPOTIFY_AVAILABLE:
        return jsonify({'error': 'Spotify credentials not configured'}), 500
    
    session_state = session.get('spotify_auth_state')
    request_state = request.args.get('state')
    
    if not session_state or not request_state:
        return redirect(url_for('index'))
    
    if session_state != request_state:
        return redirect(url_for('spotify_login'))
    
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    try:
        token_info = sp_oauth.get_access_token(code)
        session['spotify_token_info'] = token_info
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error getting token: {e}")
        return redirect(url_for('index'))

@app.route('/spotify/logout')
def spotify_logout():
    """Log out from Spotify by removing the session token"""
    if 'spotify_token_info' in session:
        session.pop('spotify_token_info')
    return redirect(url_for('index'))

def get_spotify_client():
    """Get a Spotify client instance using the cached token"""
    if not SPOTIFY_AVAILABLE:
        return None
    
    token_info = session.get('spotify_token_info')
    
    if token_info:
        now = int(time.time())
        if token_info['expires_at'] - now < 60:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['spotify_token_info'] = token_info
        
        return spotipy.Spotify(auth=token_info['access_token'])
    
    return None

@app.route('/api/spotify/current_track')
def spotify_current_track():
    """Get information about the current playing track"""
    sp = get_spotify_client()
    if not sp:
        return jsonify({'status': 'error', 'message': 'Not connected to Spotify'}), 401
    
    try:
        current = sp.current_playback()
        if not current or not current.get('item'):
            recent = sp.current_user_recently_played(limit=1)
            if recent and recent.get('items') and len(recent['items']) > 0:
                track = recent['items'][0]['track']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                
                return jsonify({
                    'status': 'success',
                    'playing': False,
                    'track': {
                        'name': track['name'],
                        'artists': artists,
                        'album': track['album']['name'],
                        'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                        'duration_ms': track['duration_ms'],
                        'progress_ms': 0,
                        'last_played': recent['items'][0]['played_at']
                    }
                })
            
            return jsonify({'status': 'success', 'playing': False, 'message': 'Nothing is currently playing'})
        
        track = current['item']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        
        return jsonify({
            'status': 'success',
            'playing': current.get('is_playing', False),
            'track': {
                'name': track['name'],
                'artists': artists,
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms'],
                'progress_ms': current.get('progress_ms', 0)
            }
        })
    except Exception as e:
        error_msg = str(e)
        if "The access token expired" in error_msg:
            return jsonify({'status': 'error', 'message': 'Your Spotify session has expired. Please reconnect.'}), 401
        
        print(f"Spotify API error: {error_msg}")
        return jsonify({'status': 'error', 'message': 'Error connecting to Spotify API'}), 500

@app.route('/api/spotify/recent_tracks')
def spotify_recent_tracks():
    """Get recently played tracks"""
    sp = get_spotify_client()
    if not sp:
        return jsonify({'status': 'error', 'message': 'Not connected to Spotify'}), 401
    
    try:
        recent_tracks = sp.current_user_recently_played(limit=5)
        if not recent_tracks or not recent_tracks.get('items'):
            return jsonify({'status': 'success', 'tracks': []})
        
        tracks = []
        for item in recent_tracks['items']:
            track = item['track']
            artists = ", ".join([artist['name'] for artist in track['artists']])
            
            tracks.append({
                'name': track['name'],
                'artists': artists,
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'played_at': item['played_at']
            })
        
        return jsonify({
            'status': 'success',
            'tracks': tracks
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/spotify/status')
def spotify_status():
    """Get the current status of Spotify connection"""
    return jsonify({
        'connected': bool(session.get('spotify_token_info')),
        'available': SPOTIFY_AVAILABLE
    })

def get_cpu_temperature():
    """Get the CPU temperature on Raspberry Pi"""
    try:
        temp = subprocess.check_output(["vcgencmd", "measure_temp"], universal_newlines=True)
        temp = float(temp.replace("temp=", "").replace("'C", ""))
        return round(temp, 1)
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000
                return round(temp, 1)
        except:
            return 0.0

def get_system_info():
    """Get system metrics including CPU, memory, and disk usage"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    memory = psutil.virtual_memory()
    memory_used = round(memory.used / (1024 * 1024 * 1024), 1)
    memory_total = round(memory.total / (1024 * 1024 * 1024), 1) 
    
    disk = shutil.disk_usage('/')
    disk_used = round(disk.used / (1024 * 1024 * 1024), 1)
    disk_total = round(disk.total / (1024 * 1024 * 1024), 1)
    
    cpu_temp = get_cpu_temperature()
    
    return {
        'cpu_temp': cpu_temp,
        'cpu_load': round(cpu_percent, 1),
        'memory_used': memory_used,
        'memory_total': memory_total,
        'disk_used': disk_used,
        'disk_total': disk_total
    }

@app.route('/api/system/stats')
def system_stats():
    """Get system statistics for the Raspberry Pi"""
    try:
        stats = get_system_info()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting system stats: {e}")
        return jsonify({
            'error': 'Could not retrieve system information',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors with a simple message"""
    return render_template('error.html', error="Page not found"), 404

if __name__ == '__main__':
    app.run(debug=True)
