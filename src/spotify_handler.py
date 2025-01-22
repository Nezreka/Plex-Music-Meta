# src/spotify_handler.py
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import time

class SpotifyHandler:
    def __init__(self, client_id, client_secret):
        self.logger = logging.getLogger('PlexMusicEnricher')
        self.last_request_time = None
        self.rate_limit_delay = 1  # Minimum seconds between requests
        self.spotify = self._init_spotify(client_id, client_secret)

    def _init_spotify(self, client_id, client_secret):
        """Initialize Spotify client."""
        try:
            self.logger.info("Initializing Spotify client...")
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            self.logger.info("Spotify client initialized successfully")
            return spotify
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify client: {str(e)}")
            raise

    def _rate_limit(self):
        """Implement rate limiting."""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def search_artist(self, artist_name):
        """Search for an artist on Spotify and return their details."""
        self._rate_limit()
        self.logger.info(f"Searching Spotify for artist: {artist_name}")
        try:
            results = self.spotify.search(q=artist_name, type='artist', limit=1)
            if results['artists']['items']:
                artist = results['artists']['items'][0]
                self.logger.info(f"Found artist on Spotify: {artist['name']}")
                self.logger.debug(f"Spotify artist details: {artist}")
                return {
                    'spotify_id': artist['id'],
                    'name': artist['name'],
                    'genres': artist['genres'],
                    'images': artist['images'],
                    'popularity': artist['popularity']
                }
            self.logger.info(f"No results found on Spotify for: {artist_name}")
            return None
        except Exception as e:
            self.logger.error(f"Error searching for artist {artist_name}: {str(e)}")
            return None

    def get_artist_details(self, spotify_id):
        """Get detailed information about an artist."""
        self._rate_limit()
        self.logger.info(f"Getting additional details for Spotify ID: {spotify_id}")
        try:
            artist = self.spotify.artist(spotify_id)
            self.logger.debug(f"Retrieved additional details: {artist}")
            return {
                'biography': None,
                'genres': artist['genres'],
                'images': artist['images'],
                'popularity': artist['popularity']
            }
        except Exception as e:
            self.logger.error(f"Error getting artist details for ID {spotify_id}: {str(e)}")
            return None