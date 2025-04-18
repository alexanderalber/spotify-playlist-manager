# this file is run only once, initially, to create the database

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
from pathlib import Path
import pandas as pd
from typing import Dict, List, Set
import envvars

class SpotifyAnalyzer:
    def __init__(self, spotify_client=None, client_id=None, client_secret=None, redirect_uri=None):
        """Initialize with existing client or create new one."""
        if spotify_client:
            self.sp = spotify_client
        else:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-library-read playlist-read-private playlist-modify-public playlist-modify-private"
            ))
        
        self.db_path = Path("spotify_cache.db")
        self.init_db()
    
    
    def init_db(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS liked_songs (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    artist TEXT,
                    added_at TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS playlists (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    owner_id TEXT
                );
                
                CREATE TABLE IF NOT EXISTS playlist_songs (
                    playlist_id TEXT,
                    song_id TEXT,
                    FOREIGN KEY(playlist_id) REFERENCES playlists(id),
                    FOREIGN KEY(song_id) REFERENCES liked_songs(id),
                    PRIMARY KEY(playlist_id, song_id)
                );

                CREATE TABLE IF NOT EXISTS played_history (
                    song_id TEXT,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(song_id) REFERENCES liked_songs(id),
                    PRIMARY KEY(song_id, played_at)
                );
            """)
    

    def fetch_all_liked_songs(self):
        """Fetch all liked songs and store in database."""
        print("Fetching liked songs...")
        results = self.sp.current_user_saved_tracks()
        count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            while results:
                for item in results['items']:
                    track = item['track']
                    conn.execute("""
                        INSERT OR REPLACE INTO liked_songs (id, name, artist, added_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        track['id'],
                        track['name'],
                        track['artists'][0]['name'],
                        item['added_at']
                    ))
                    count += 1
                
                if results['next']:
                    results = self.sp.next(results)
                else:
                    results = None
        
        print(f"Stored {count} liked songs")
    

    def fetch_all_playlists(self):
        """Fetch all user playlists and their songs."""
        print("Fetching playlists...")
        playlists = self.sp.current_user_playlists()
        
        # Get current user id
        user_info = self.sp.current_user()
        user_id = user_info['id']
        print(f"Current user: {user_id}")
        
        own_playlist_count = 0
        followed_playlist_count = 0
        total_tracks = 0
        
        with sqlite3.connect(self.db_path) as conn:
            while playlists:
                for playlist in playlists['items']:
                    # Store playlist info with owner
                    conn.execute("""
                        INSERT OR REPLACE INTO playlists (id, name, owner_id)
                        VALUES (?, ?, ?)
                    """, (
                        playlist['id'],
                        playlist['name'],
                        playlist['owner']['id']
                    ))
                    
                    # Only fetch tracks for owned playlists
                    if playlist['owner']['id'] == user_id:
                        own_playlist_count += 1
                        print(f"Fetching tracks for owned playlist: {playlist['name']}")
                        
                        # Fetch and store all tracks in playlist
                        results = self.sp.playlist_tracks(playlist['id'])
                        while results:
                            for item in results['items']:
                                if item['track']:  # Some tracks might be None due to availability
                                    conn.execute("""
                                        INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
                                        VALUES (?, ?)
                                    """, (playlist['id'], item['track']['id']))
                                    total_tracks += 1
                            
                            if results['next']:
                                results = self.sp.next(results)
                            else:
                                results = None
                    else:
                        followed_playlist_count += 1
                        print(f"Skipping tracks for followed playlist: {playlist['name']}")
                
                if playlists['next']:
                    playlists = self.sp.next(playlists)
                else:
                    playlists = None
        
        print(f"\nSummary:")
        print(f"- Own playlists: {own_playlist_count}")
        print(f"- Followed playlists: {followed_playlist_count}")
        print(f"- Total tracks in own playlists: {total_tracks}")
    

    def analyze_songs(self) -> pd.DataFrame:
        """Create a DataFrame showing which songs are in which playlists."""
        with sqlite3.connect(self.db_path) as conn:
            # Get current user id
            user_id = self.sp.current_user()['id']
            
            # Get all liked songs
            liked_songs = pd.read_sql("""
                SELECT id, name, artist, added_at 
                FROM liked_songs
                ORDER BY added_at DESC
            """, conn)
            
            # Get only owned playlists
            playlists = pd.read_sql("""
                SELECT id, name 
                FROM playlists 
                WHERE owner_id = ?
            """, conn, params=[user_id])
            
            # Get playlist memberships for owned playlists
            memberships = pd.read_sql("""
                SELECT ps.* 
                FROM playlist_songs ps
                JOIN playlists p ON ps.playlist_id = p.id
                WHERE p.owner_id = ?
            """, conn, params=[user_id])
            
            # Create pivot table with all possible combinations
            # First, get all possible song_id x playlist_id combinations
            all_songs = liked_songs['id']
            all_playlists = playlists['id']
            
            # Create a MultiIndex with all combinations
            multi_idx = pd.MultiIndex.from_product(
                [all_songs, all_playlists],
                names=['song_id', 'playlist_id']
            )
            
            # Reindex memberships to include all combinations
            full_memberships = pd.DataFrame(
                index=multi_idx
            ).reset_index()
            
            # Merge with actual memberships
            full_memberships['exists'] = full_memberships.apply(
                lambda x: 1 if memberships[
                    (memberships['song_id'] == x['song_id']) & 
                    (memberships['playlist_id'] == x['playlist_id'])
                ].shape[0] > 0 else 0,
                axis=1
            )
            
            # Create pivot table
            pivot = pd.pivot_table(
                full_memberships,
                values='exists',
                index='song_id',
                columns='playlist_id',
                fill_value=0
            )
            
            # Merge with song info
            result = liked_songs.merge(
                pivot,
                left_on='id',
                right_index=True,
                how='left'
            )
            
            # Rename playlist columns to playlist names
            playlist_names = dict(zip(playlists.id, playlists.name))
            result = result.rename(columns=playlist_names)
            
            return result


    def cleanup_deleted_items(self):
        """Remove items that no longer exist in Spotify."""
        print("Starting cleanup of deleted items...")
        
        # Get current state from Spotify
        current_songs = set()
        results = self.sp.current_user_saved_tracks()
        while results:
            for item in results['items']:
                current_songs.add(item['track']['id'])
            if results['next']:
                results = self.sp.next(results)
            else:
                results = None
        
        current_playlists = {
            p['id'] 
            for p in self.sp.current_user_playlists()['items']
        }
        
        with sqlite3.connect(self.db_path) as conn:
            # Get counts before cleanup
            before_songs = conn.execute("SELECT COUNT(*) FROM liked_songs").fetchone()[0]
            before_playlists = conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
            before_memberships = conn.execute("SELECT COUNT(*) FROM playlist_songs").fetchone()[0]
            
            # Remove deleted songs
            if current_songs:
                placeholders = ','.join('?' * len(current_songs))
                conn.execute(f"""
                    DELETE FROM liked_songs 
                    WHERE id NOT IN ({placeholders})
                """, list(current_songs))
            
            # Remove deleted playlists
            if current_playlists:
                placeholders = ','.join('?' * len(current_playlists))
                conn.execute(f"""
                    DELETE FROM playlists 
                    WHERE id NOT IN ({placeholders})
                """, list(current_playlists))
            
            # Cleanup orphaned playlist_songs entries
            conn.execute("""
                DELETE FROM playlist_songs
                WHERE song_id NOT IN (SELECT id FROM liked_songs)
                OR playlist_id NOT IN (SELECT id FROM playlists)
            """)
            
            # Get counts after cleanup
            after_songs = conn.execute("SELECT COUNT(*) FROM liked_songs").fetchone()[0]
            after_playlists = conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
            after_memberships = conn.execute("SELECT COUNT(*) FROM playlist_songs").fetchone()[0]
            
            print(f"\nCleanup summary:")
            print(f"- Songs: {before_songs} -> {after_songs} (-{before_songs - after_songs})")
            print(f"- Playlists: {before_playlists} -> {after_playlists} (-{before_playlists - after_playlists})")
            print(f"- Memberships: {before_memberships} -> {after_memberships} (-{before_memberships - after_memberships})")



def main():
    CLIENT_ID = envvars.client_id
    CLIENT_SECRET = envvars.client_secret
    REDIRECT_URI = "http://localhost:8888/callback"
    
    analyzer = SpotifyAnalyzer(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)
    
    print("Starting initial data load...")
    analyzer.fetch_all_liked_songs()
    analyzer.fetch_all_playlists()
    
    print("\nAnalyzing data...")
    df = analyzer.analyze_songs()
    
    print("\nSample of the analysis:")
    print(df.head())
    
    # Export to CSV for further analysis
    df.to_csv("spotify_analysis.csv", index=False)
    print("\nFull analysis exported to spotify_analysis.csv")

if __name__ == "__main__":
    main()