from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps
import sqlite3
import pandas as pd
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from read_from_spotify import SpotifyAnalyzer
import envvars
from typing import Callable, Any, TypeVar, Optional, Dict, List
import traceback

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Type hints
F = TypeVar('F', bound=Callable[..., Any])

# Spotify setup
auth_manager = SpotifyOAuth(
    client_id=envvars.client_id,
    client_secret=envvars.client_secret,
    redirect_uri="http://localhost:8888/callback",
    scope="user-library-read user-library-modify playlist-read-private playlist-modify-public playlist-modify-private streaming user-read-playback-state user-modify-playback-state",
    cache_handler=spotipy.cache_handler.FlaskSessionCacheHandler(session)
)

# Database helper class
class Database:
    def __init__(self, db_path: str = 'spotify_cache.db'):
        self.db_path = db_path

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

# Decorators
def require_auth(f: F) -> F:
    """Ensure user is authenticated before proceeding."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('token_info'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def handle_errors(f: F) -> F:
    """Global error handling for routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    return decorated

# Spotify client helper
def get_spotify() -> Optional[spotipy.Spotify]:
    """Get spotify client, creating if needed."""
    if not session.get('token_info'):
        return None
    return spotipy.Spotify(auth_manager=auth_manager)

# Route handlers
@app.route('/')
@require_auth
@handle_errors
def index():
    """Render the main page with song data."""
    spotify = get_spotify()
    user_info = spotify.current_user()
    user_id = user_info['id']
    
    with Database() as conn:
        # Get basic data
        songs = conn.execute('SELECT * FROM liked_songs ORDER BY added_at DESC').fetchall()
        playlists = spotify.current_user_playlists()
        
        # Process playlists
        owned_playlists = []
        for playlist in playlists['items']:
            if playlist['owner']['id'] == user_id:
                owned_playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name']
                })
                conn.execute("""
                    INSERT OR REPLACE INTO playlists (id, name, owner_id)
                    VALUES (?, ?, ?)
                """, (playlist['id'], playlist['name'], user_id))
        
        # Get memberships for owned playlists
        owned_playlist_ids = [p['id'] for p in owned_playlists]
        if owned_playlist_ids:
            placeholders = ','.join('?' * len(owned_playlist_ids))
            memberships = conn.execute(
                f"SELECT * FROM playlist_songs WHERE playlist_id IN ({placeholders})",
                owned_playlist_ids
            ).fetchall()
        else:
            memberships = []
            
        # Get played songs
        played_songs = conn.execute(
            "SELECT DISTINCT song_id FROM played_history"
        ).fetchall()
        
        conn.commit()

    # Process data for template
    songs_list = [dict(s) for s in songs]
    memberships_set = {(m['song_id'], m['playlist_id']) for m in memberships}
    played_songs_set = {s['song_id'] for s in played_songs}
    
    # Add special "Liked Songs" playlist
    liked_songs_playlist = {'id': 'liked_songs', 'name': '❤️ Liked Songs'}
    owned_playlists.insert(0, liked_songs_playlist)
    
    # Get fresh token
    token = auth_manager.get_cached_token()['access_token']
    
    # Helper function for template
    def song_in_playlist(song_id: str, playlist_id: str) -> bool:
        if playlist_id == 'liked_songs':
            return True
        return (song_id, playlist_id) in memberships_set
    
    return render_template(
        'index.html',
        songs=songs_list,
        playlists=owned_playlists,
        song_in_playlist=song_in_playlist,
        song_was_played=lambda s: s in played_songs_set,
        spotify_token=token
    )

@app.route('/login')
def login():
    """Handle login flow."""
    auth_url = auth_manager.get_authorize_url()
    print(f"Redirecting to auth URL: {auth_url}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Handle auth callback."""
    code = request.args.get('code')
    token_info = auth_manager.get_access_token(code)
    session['token_info'] = token_info
    return redirect('/')

# API Routes
@app.route('/api/toggle_playlist', methods=['POST'])
@require_auth
@handle_errors
def toggle_playlist():
    """Add or remove a song from a playlist."""
    spotify = get_spotify()
    data = request.json
    song_id = data['song_id']
    playlist_id = data['playlist_id']
    
    with Database() as conn:
        exists = conn.execute("""
            SELECT 1 FROM playlist_songs 
            WHERE song_id = ? AND playlist_id = ?
        """, (song_id, playlist_id)).fetchone()
        
        if exists:
            spotify.playlist_remove_all_occurrences_of_items(
                playlist_id=playlist_id,
                items=[song_id]
            )
            conn.execute("""
                DELETE FROM playlist_songs 
                WHERE song_id = ? AND playlist_id = ?
            """, (song_id, playlist_id))
        else:
            spotify.playlist_add_items(
                playlist_id=playlist_id,
                items=[song_id]
            )
            conn.execute("""
                INSERT INTO playlist_songs (song_id, playlist_id)
                VALUES (?, ?)
            """, (song_id, playlist_id))
        
        conn.commit()
    
    return jsonify({'status': 'success', 'in_playlist': not exists})

@app.route('/api/play', methods=['POST'])
@require_auth
@handle_errors
def play_song():
    """Start playback of a specific song."""
    spotify = get_spotify()
    song_id = request.json['song_id']
    
    # Get available devices
    devices = spotify.devices()
    if not devices['devices']:
        return jsonify({'error': 'No active devices found'}), 400
    
    # Find active device
    active_devices = [d for d in devices['devices'] if d['is_active']]
    device_id = active_devices[0]['id'] if active_devices else devices['devices'][0]['id']
    
    # Start playback
    spotify.start_playback(
        device_id=device_id,
        uris=[f'spotify:track:{song_id}']
    )
    
    return jsonify({'status': 'success'})

@app.route('/api/stop', methods=['POST'])
@require_auth
@handle_errors
def stop_playback():
    """Stop current playback."""
    spotify = get_spotify()
    try:
        # Only try to stop if something is actually playing
        playback = spotify.current_playback()
        if playback and playback['is_playing']:
            spotify.pause_playback()
    except Exception as e:
        print(f"Error stopping playback: {e}")
        # Don't error out - the UI can handle it
        pass
    
    return jsonify({'status': 'success'})

@app.route('/api/mark_played', methods=['POST'])
@require_auth
@handle_errors
def mark_played():
    """Mark a song as played."""
    song_id = request.json['song_id']
    
    with Database() as conn:
        conn.execute("""
            INSERT INTO played_history (song_id)
            VALUES (?)
        """, (song_id,))
        conn.commit()
    
    return jsonify({'status': 'success'})

@app.route('/api/refresh', methods=['POST'])
@require_auth
@handle_errors
def refresh_data():
    """Refresh all data from Spotify."""
    spotify = get_spotify()
    analyzer = SpotifyAnalyzer(spotify_client=spotify)
    
    analyzer.cleanup_deleted_items()
    analyzer.fetch_all_liked_songs()
    analyzer.fetch_all_playlists()
    
    return jsonify({'status': 'success'})

@app.route('/api/seek', methods=['POST'])
@require_auth
@handle_errors
def seek_playback():
    """Seek forward/backward in current playback."""
    spotify = get_spotify()
    position_ms = request.json['position_ms']
    
    playback = spotify.current_playback()
    if not playback:
        return jsonify({'error': 'No active playback'}), 400
    
    current_ms = playback['progress_ms']
    track_duration = playback['item']['duration_ms']
    new_position = max(0, min(current_ms + position_ms, track_duration))
    
    spotify.seek_track(new_position)
    return jsonify({'status': 'success', 'new_position': new_position})

@app.route('/api/unlike_song', methods=['POST'])
@require_auth
@handle_errors
def unlike_song():
    """Remove a song from liked songs."""
    spotify = get_spotify()
    song_id = request.json['song_id']
    spotify.current_user_saved_tracks_delete([song_id])
    return jsonify({'status': 'success'})

@app.route('/api/like_song', methods=['POST'])
@require_auth
@handle_errors
def like_song():
    """Add a song back to liked songs."""
    spotify = get_spotify()
    song_id = request.json['song_id']
    spotify.current_user_saved_tracks_add([song_id])
    return jsonify({'status': 'success'})

@app.route('/api/playback_status')
@require_auth
@handle_errors
def get_playback_status():
    """Get current playback status."""
    spotify = get_spotify()
    playback = spotify.current_playback()
    
    if not playback or not playback['is_playing']:
        return jsonify({
            'is_playing': False,
            'progress_ms': 0,
            'duration_ms': 0
        })
    
    return jsonify({
        'is_playing': playback['is_playing'],
        'progress_ms': playback['progress_ms'],
        'duration_ms': playback['item']['duration_ms']
    })

if __name__ == '__main__':
    app.run(debug=True, port=8888)