# Spotify Playlist Manager

A web application to efficiently manage your Spotify liked songs across multiple playlists. The app provides a simple interface to view and organize your liked songs, making it easier to add or remove tracks from your playlists.

![Spotify Playlist Manager Screenshot](/docs/screenshot.PNG)

## Features

- View all your liked songs in one place
- See which songs are in which playlists at a glance
- Easily add/remove songs to/from multiple playlists
- Trigger song playback directly from the interface

## Prerequisites

- Python 3.10 (other versions might work but are untested)
- Spotify Premium account 
- Spotify Developer account for API access

## Setup

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

4. Configure your Spotify credentials:
   - Create a file named `envvars.py`
   - Add your Spotify API credentials (see "Spotify Setup" below):
   ```python
   client_id = "your_client_id_here"
   client_secret = "your_client_secret_here"
   ```
   - Keep this file secure and never commit it to version control

5. Initialize the database:
```bash
python read_from_spotify.py
```

6. Open the native Spotify app on the device of your choice

7. Run the application:
```bash
python app.py
```

8. Open your browser and navigate to `http://localhost:8888`

## Spotify Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Set the redirect URI to `http://localhost:8888/callback`
4. Copy your Client ID and Client Secret 
5. In the App settings, activate Web API and Web Playback SDK


## Project Structure

```
spotify-playlist-manager/
├── app.py               # Main Flask application
├── read_from_spotify.py # Initial database setup
├── envvars.py           # Spotify API credentials (you need to create this)
├── requirements.txt    
├── docs/
│   └── screenshot.png     
├── static/
│   └── styles.css    
├── templates/
│   └── index.html     
└── spotify_cache.db     # Local database (generated)
```

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
