# Plex Music Meta

A Python command-line application that automatically enriches your Plex music library metadata by fetching artist information from Spotify.

## Features

- Automatically matches Plex artists with Spotify artists
- Updates missing or invalid artist images using:
  - Spotify artist profile pictures
  - Album art as a fallback if no Spotify image is available
- Enhances artist genres by combining:
  - Existing Plex genres
  - Spotify artist genres
  - Album genres
- Validates image quality and format before updating
- Maintains a database of processed artists
- Progress tracking for large libraries
- Detailed logging of all operations
- Graceful error handling

## Prerequisites

- Python 3.8 or higher
- Plex server with a music library
- Spotify Developer API credentials
- Access to your Plex server's API

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Nezreka/Plex-Music-Meta.git
   cd plex-music-meta
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  
   ```
3. Create and activate a virtual environment on Windows:
   ```bash
   python -m venv venv
   venv\Scripts\activate  
   ```
4. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Rename 'config.json.example' to 'config.json'&#x20;

## Configuration

Create a `config.json` file in the project root with the following structure:

```json
{
    "plex": {
        "base_url": "http://your-plex-server:32400",
        "token": "your-plex-token"
    },
    "spotify": {
        "client_id": "your-spotify-client-id",
        "client_secret": "your-spotify-client-secret"
    },
    "database": {
        "path": "artists.db"
    },
    "logging": {
        "path": "logs/app.log",
        "level": "DEBUG"
    }
}
```

### Getting Required Credentials

1. **Plex Token:**
   - Sign in to Plex
   - Visit account settings
   - Find your token under the authorized devices section
2. **Spotify API Credentials:**
   - Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new application
   - Get your Client ID and Client Secret

## Usage

Run the application:

```bash
python src/main.py
```

The application will:

1. Connect to your Plex server
2. Retrieve all music artists
3. Check each artist against the processed database
4. For unprocessed artists:
   - Search for matching artist on Spotify
   - Download and validate artist images if not existing
   - Update artist genres
   - Store processing results in the database

## Project Structure

```
plex-music-meta/
├── database/
│   ├── artists.db
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config_handler.py
│   ├── database_handler.py
│   ├── plex_handler.py
│   └── spotify_handler.py
│   └── logger.py
├── config.json
├── requirements.txt
└── README.md
```

## File Descriptions

- `main.py`: Application entry point and main logic
- `config_handler.py`: Handles configuration file loading and validation
- `database_handler.py`: Manages SQLite database for tracking processed artists
- `plex_handler.py`: Handles all Plex server interactions and metadata updates
- `spotify_handler.py`: Manages Spotify API interactions and artist searches

## Error Handling

The application includes comprehensive error handling:

- Invalid configurations
- Network connectivity issues
- API rate limiting
- Invalid image formats
- Database errors

All errors are logged with detailed information for troubleshooting.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- PlexAPI for Python
- Spotipy (Spotify API wrapper)
- TQDM for progress bars
- Pillow for image processing

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.

