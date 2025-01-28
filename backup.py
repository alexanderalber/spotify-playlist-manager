

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from datetime import datetime
from pathlib import Path
import logging
import envvars

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_playlists(sp):
    """Backup all playlists and their tracks."""
    backup = {}
    
    # Get all user playlists
    playlists = sp.current_user_playlists()
    logger.info(f"Found {playlists['total']} playlists")
    
    while playlists:
        for playlist in playlists['items']:
            playlist_id = playlist['id']
            playlist_name = playlist['name']
            
            # Get all tracks for this playlist
            tracks = []
            results = sp.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    if item['track']:  # Some tracks might be None due to availability
                        track = item['track']
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                            'added_at': item['added_at']
                        })
                
                if results['next']:
                    results = sp.next(results)
                else:
                    results = None
            
            backup[playlist_name] = {
                'id': playlist_id,
                'tracks': tracks
            }
            logger.info(f"Backed up playlist '{playlist_name}' with {len(tracks)} tracks")
        
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None
    
    return backup

def main():
    # Configure Spotify client
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id = envvars.client_id,
    client_secret = envvars.client_secret,
    redirect_uri="http://localhost:8888/callback",
    scope="playlist-read-private playlist-read-collaborative"
    ))
    
    # Create backup
    backup = backup_playlists(sp)
    
    # Create backup directory if it doesn't exist
    backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)
    
    # Save backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'spotify_backup_{timestamp}.json'
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Backup saved to {backup_file}")
    
    # Create a summary
    summary = {name: len(data['tracks']) for name, data in backup.items()}
    logger.info("\nBackup Summary:")
    for playlist, count in summary.items():
        logger.info(f"{playlist}: {count} tracks")

if __name__ == "__main__":
    main()