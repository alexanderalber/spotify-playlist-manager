
from flask import Flask, render_template, jsonify, request, redirect, session
import sqlite3
import pandas as pd
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from read_from_spotify import SpotifyAnalyzer
import envvars


app = Flask(__name__)
app.secret_key = os.urandom(24) 


auth_manager = SpotifyOAuth(
    client_id=envvars.client_id,
    client_secret=envvars.client_secret,
    redirect_uri="http://localhost:8888/callback",
    scope="user-library-read user-library-modify playlist-read-private playlist-modify-public playlist-modify-private streaming user-read-playback-state user-modify-playback-state",
    cache_handler=spotipy.cache_handler.FlaskSessionCacheHandler(session)
)


def get_spotify():
    """Get spotify client, creating if needed."""
    if not session.get('token_info'):
        return None
    return spotipy.Spotify(auth_manager=auth_manager)


def get_db_connection():
    conn = sqlite3.connect('spotify_cache.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Render the main page with song data."""
    
    # Check if we need to authenticate
    if not session.get('token_info'):
        print("No token found, redirecting to auth")
        return redirect('/login')
        
    try:
        print("\nStarting data load...")
        spotify = get_spotify()
        
        # Get user ID first
        user_info = spotify.current_user()
        user_id = user_info['id']
        print(f"Loading data for user: {user_id}")
        
        conn = get_db_connection()
        
        # Get basic data, filtering for owned playlists
        songs = conn.execute('SELECT * FROM liked_songs ORDER BY added_at DESC').fetchall()
        playlists = spotify.current_user_playlists()
        
        # Filter for owned playlists and store in db
        owned_playlists = []
        for playlist in playlists['items']:
            if playlist['owner']['id'] == user_id:
                owned_playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name']
                })
                # Update in db
                conn.execute("""
                    INSERT OR REPLACE INTO playlists (id, name, owner_id)
                    VALUES (?, ?, ?)
                """, (playlist['id'], playlist['name'], user_id))
        
        # Get memberships only for owned playlists
        owned_playlist_ids = [p['id'] for p in owned_playlists]
        memberships = conn.execute("""
            SELECT * FROM playlist_songs 
            WHERE playlist_id IN ({})
        """.format(','.join('?' * len(owned_playlist_ids))), owned_playlist_ids).fetchall()
        
        conn.commit()
        
        print(f"\nLoaded:")
        print(f"- {len(songs)} songs")
        print(f"- {len(owned_playlists)} owned playlists")
        print(f"- {len(memberships)} memberships")
        
        # Convert to dicts
        songs_list = [dict(s) for s in songs]
        
        # Create membership set
        memberships_set = {
            (m['song_id'], m['playlist_id']) 
            for m in memberships
        }
        
        # Get fresh token
        token = auth_manager.get_cached_token()['access_token']
        

        played_songs = conn.execute("""
            SELECT DISTINCT song_id 
            FROM played_history
        """).fetchall()
        played_songs_set = {s['song_id'] for s in played_songs}


        liked_songs_playlist = {
        'id': 'liked_songs',  # special ID for liked songs
        'name': '❤️ Liked Songs'
        }
        owned_playlists.insert(0, liked_songs_playlist)


        def song_in_playlist(song_id, playlist_id, memberships_set):
            if playlist_id == 'liked_songs':
                return True  # all songs in this list are liked
            return (song_id, playlist_id) in memberships_set


        return render_template(
            'index.html',
            songs=songs_list,
            playlists=owned_playlists,
            song_in_playlist=lambda s, p: song_in_playlist(s, p, memberships_set),
            song_was_played=lambda s: s in played_songs_set,
            spotify_token=token
        )
        
    except Exception as e:
        print(f"Error in index: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return str(e), 500
        
    except Exception as e:
        print(f"Error in index: {str(e)}")
        return str(e), 500


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
    
    print(f"Got callback with code: {code[:10]}...")
    
    token_info = auth_manager.get_access_token(code)
    session['token_info'] = token_info
    
    print("Token stored in session")
    
    return redirect('/')


@app.route('/api/toggle_playlist', methods=['POST'])
def toggle_playlist():
    """Add or remove a song from a playlist."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        data = request.json
        song_id = data['song_id']
        playlist_id = data['playlist_id']
        
        print(f"\nToggling song {song_id} in playlist {playlist_id}")
        
        conn = get_db_connection()
        exists = conn.execute("""
            SELECT 1 FROM playlist_songs 
            WHERE song_id = ? AND playlist_id = ?
        """, (song_id, playlist_id)).fetchone()
        
        print(f"Song exists in playlist: {exists is not None}")
        
        if exists:
            # Remove from playlist
            spotify.playlist_remove_all_occurrences_of_items(
                playlist_id=playlist_id,
                items=[song_id]
            )
            conn.execute("""
                DELETE FROM playlist_songs 
                WHERE song_id = ? AND playlist_id = ?
            """, (song_id, playlist_id))
            print("Removed from playlist")
        else:
            # Add to playlist
            spotify.playlist_add_items(
                playlist_id=playlist_id,
                items=[song_id]
            )
            conn.execute("""
                INSERT INTO playlist_songs (song_id, playlist_id)
                VALUES (?, ?)
            """, (song_id, playlist_id))
            print("Added to playlist")
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'in_playlist': not exists})
        
    except Exception as e:
        print(f"Error in toggle_playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_playback():
    """Stop current playback."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        spotify.pause_playback()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in stop_playback: {str(e)}")
        return jsonify({'error': str(e)}), 500

        
@app.route('/api/play', methods=['POST'])
def play_song():
    """Start playback of a specific song."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        data = request.json
        song_id = data['song_id']
        
        # Get list of available devices
        devices = spotify.devices()
        
        if not devices['devices']:
            return jsonify({'error': 'No active devices found'}), 400
        
        # Find active device
        active_devices = [d for d in devices['devices'] if d['is_active']]
        if not active_devices:
            device_id = devices['devices'][0]['id']
        else:
            device_id = active_devices[0]['id']
        
        print(f"Playing on device: {device_id}")
        
        # Start playback
        spotify.start_playback(
            device_id=device_id,
            uris=[f'spotify:track:{song_id}']
        )
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in play_song: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mark_played', methods=['POST'])
def mark_played():
    """Mark a song as played."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        data = request.json
        song_id = data['song_id']
        
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO played_history (song_id)
            VALUES (?)
        """, (song_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error marking song as played: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Refresh all data from Spotify."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        # Use existing spotify client instead of creating new auth
        spotify = get_spotify()
        
        # Initialize analyzer with existing spotify client
        analyzer = SpotifyAnalyzer(spotify_client=spotify)
        
        # Perform cleanup first
        analyzer.cleanup_deleted_items()
        
        # Then fetch fresh data
        analyzer.fetch_all_liked_songs()
        analyzer.fetch_all_playlists()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in refresh: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/seek', methods=['POST'])
def seek_playback():
    """Seek forward/backward in current playback."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        data = request.json
        position_ms = data['position_ms']  # position in milliseconds
        
        # Get current playback state
        playback = spotify.current_playback()
        if not playback:
            return jsonify({'error': 'No active playback'}), 400
            
        # Calculate new position
        current_ms = playback['progress_ms']
        new_position = current_ms + position_ms
        
        # Ensure we don't seek past track bounds
        track_duration = playback['item']['duration_ms']
        new_position = max(0, min(new_position, track_duration))
        
        # Seek to new position
        spotify.seek_track(new_position)
        
        return jsonify({'status': 'success', 'new_position': new_position})
        
    except Exception as e:
        print(f"Error in seek_playback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/unlike_song', methods=['POST'])
def unlike_song():
    """Remove a song from liked songs."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        data = request.json
        song_id = data['song_id']
        
        # Remove from Spotify liked songs
        spotify.current_user_saved_tracks_delete([song_id])

        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in unlike_song: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/like_song', methods=['POST'])
def like_song():
    """Add a song back to liked songs."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        spotify = get_spotify()
        data = request.json
        song_id = data['song_id']
        
        # Add to Spotify liked songs
        spotify.current_user_saved_tracks_add([song_id])
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in like_song: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/playback_status')
def get_playback_status():
    """Get current playback status."""
    if not session.get('token_info'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
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
        
    except Exception as e:
        print(f"Error getting playback status: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8888)