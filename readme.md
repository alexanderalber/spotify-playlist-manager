# Spotify Playlist Manager

A web application to efficiently manage your Spotify liked songs across multiple playlists. The app provides a simple interface to view and organize your liked songs, making it easier to add or remove tracks from your playlists.

![Spotify Playlist Manager Screenshot](/docs/screenshot.PNG)

## Features
- View all your liked songs in one place
- See which songs are in which playlists at a glance
- Easily add/remove songs to/from multiple playlists
- Control song playback directly from the interface
- Dark/Light mode
- Already played songs are marked
- Keyboard navigation for power users

## Prerequisites

- Python 3.10 (other versions might work but are untested)
- Spotify Premium account 

## Spotify Setup

1. Go to [Spotify Developer Portal](https://developer.spotify.com) and make yourself a developer
2. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) 
3. Create a new application
4. Set the redirect URI to `http://localhost:8888/callback`
5. Copy your Client ID and Client Secret 
6. In the App settings, activate Web API and Web Playback SDK

## Python Setup

1. Clone the repository:
```bash
git clone https://github.com/alexanderalber/spotify-playlist-manager
cd spotify-playlist-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Enter your Spotify credentials:
   - Create a file named `envvars.py`
   - Add your Spotify API credentials:
   ```python
   client_id = "your_client_id_here"
   client_secret = "your_client_secret_here"
   ```
   - Keep this file secure and never commit it to version control

5. Initialize the database (your browser might open and Spotify might ask for permission):
```bash
python read_from_spotify.py
```

## Usage

1. Make sure that Spotify is open and running somewhere. This app does not actually play music by itself, it will instead trigger playback on the actual Spotify app. 

2. Run the application (your browser might open and Spotify might ask for permission):
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:8888`

### Controls
- **Mouse Controls:**
  - Click cells to toggle playlist membership
  - Click play button to start/stop playback
  - Click anywhere in a row to select it for keyboard controls
  - Click the sun/moon icon to toggle dark/light theme
  - Click refresh to update data from Spotify

- **Keyboard Controls:**
  - ↑/↓: Navigate through songs
  - Space: Play/stop selected song
  - 1-9: Quick-toggle playlists
  - Esc: Stop playback
  - ←/→: Skip 20s backward/forward

### Behavior Notes
- Playlist memberships (cells) are updated on Spotify instantly - no refresh necessary
- Songs already played in this app are marked with color
- Dark/light theme persists across sessions
- Refresh button updates:
  - Removes unliked songs
  - Adds new liked songs
  - Updates playlist structure
  - Can take 10-20 seconds for large libraries

## Project Structure

```
spotify-playlist-manager/
├── app.py               # Main Flask application
├── read_from_spotify.py # Initial database setup
├── envvars.py           # Spotify API credentials (you need to create this)
├── backup.py            # Save Playlists to json
├── requirements.txt    
├── static/
│   ├── css/
│   │   └── styles.css  
│   └── js/
│       ├── utils.js           
│       ├── ui-manager.js      
│       ├── playlist-manager.js 
│       ├── playback-manager.js
│       ├── navigation-manager.js 
│       └── keyboard-manager.js 
├── templates/
│   └── index.html     
└── spotify_cache.db    # Local database (generated by running read_from_spotify.py)
```

## Development

The application uses a modular JavaScript architecture:
- `utils.js`: Common utility functions and API calls
- `ui-manager.js`: Handles UI state and theme
- `playlist-manager.js`: Manages playlist operations
- `playback-manager.js`: Controls music playback
- `navigation-manager.js`: Handles row selection and navigation
- `keyboard-manager.js`: Manages keyboard shortcuts

The Flask backend provides:
- Authentication with Spotify
- Database management
- API endpoints for all operations
- Static file serving

## License

This project is licensed under a modified MIT License with additional restrictions:

1. Personal and educational use is permitted
2. Commercial use requires explicit permission from the author
3. Modifications and improvements are welcome, but must be shared under the same license terms

For commercial licensing inquiries, please contact the repository owner.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

When contributing:
1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request with a clear description of the changes

## Troubleshooting

- If playback doesn't work, make sure Spotify is running somewhere
- If authentication fails, check your API credentials
- To reset play markers, delete spotify_cache.db and rerun read_from_spotify.py
- For other issues, check the Python console output