# src/plex_handler.py
from plexapi.server import PlexServer
import logging
import requests
from urllib.parse import urlparse
import os
import time
from concurrent.futures import ThreadPoolExecutor
import threading

class PlexHandler:
    def __init__(self, base_url, token):
        self.logger = logging.getLogger('PlexMusicEnricher')
        self.server = self._connect_to_plex(base_url, token)
        self.music_library = self._get_music_library()
        self.thread_lock = threading.Lock()
        self.max_workers = 4  # Adjust based on your system

    def process_artist_batch(self, artists, db_handler, spotify_handler):
        """Process a batch of artists in parallel."""
        def process_single_artist(artist):
            try:
                with self.thread_lock:
                    if db_handler.is_artist_processed(artist.ratingKey):
                        return None

                spotify_data = spotify_handler.search_artist(artist.title)
                if spotify_data:
                    details = spotify_handler.get_artist_details(spotify_data['spotify_id'])
                    if details:
                        spotify_data.update(details)

                    success = self.update_artist_metadata(artist, spotify_data)
                    
                    with self.thread_lock:
                        db_handler.mark_artist_processed(
                            artist.ratingKey,
                            artist.title,
                            spotify_id=spotify_data['spotify_id'],
                            success=success
                        )
                    return artist.title
                else:
                    with self.thread_lock:
                        db_handler.mark_artist_processed(
                            artist.ratingKey,
                            artist.title,
                            success=False,
                            error_message="Not found on Spotify"
                        )
                    return None

            except Exception as e:
                self.logger.error(f"Error processing artist {artist.title}: {str(e)}")
                with self.thread_lock:
                    db_handler.mark_artist_processed(
                        artist.ratingKey,
                        artist.title,
                        success=False,
                        error_message=str(e)
                    )
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_single_artist, artist) for artist in artists]
            return [f.result() for f in futures if f.result() is not None]

    def _connect_to_plex(self, base_url, token):
        """Establish connection to Plex server."""
        try:
            server = PlexServer(base_url, token)
            self.logger.info("Successfully connected to Plex server")
            return server
        except Exception as e:
            self.logger.error(f"Failed to connect to Plex server: {str(e)}")
            raise

    def _get_music_library(self):
        """Get the music library section."""
        try:
            music_sections = [section for section in self.server.library.sections() if section.type == 'artist']
            if not music_sections:
                raise Exception("No music library found")
            return music_sections[0]
        except Exception as e:
            self.logger.error(f"Failed to get music library: {str(e)}")
            raise

        

    def get_all_artists(self):
        """Retrieve all artists from the music library."""
        try:
            return self.music_library.all()
        except Exception as e:
            self.logger.error(f"Failed to retrieve artists: {str(e)}")
            return []

    def _download_image(self, url):
        """Download image from URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.logger.error(f"Failed to download image from {url}: {str(e)}")
            return None
            
    def _validate_image(self, image_data):
        """Validate image data before upload."""
        try:
            from PIL import Image
            import io
            
            # Try to open the image data with PIL to verify it's valid
            image = Image.open(io.BytesIO(image_data))
            
            # Get image details for logging
            format = image.format
            width, height = image.size
            self.logger.info(f"Validating image: Format={format}, Size={width}x{height}")

            # Check minimum dimensions
            if width < 200 or height < 200:
                self.logger.error(f"Image too small: {width}x{height}")
                return None

            # Convert to JPEG if it's not JPEG or PNG
            if format not in ['JPEG', 'PNG']:
                self.logger.info("Converting image to JPEG")
                buffer = io.BytesIO()
                image.convert('RGB').save(buffer, format='JPEG', quality=95)
                return buffer.getvalue()
            
            # If it's PNG, convert to JPEG for consistency
            if format == 'PNG':
                self.logger.info("Converting PNG to JPEG")
                buffer = io.BytesIO()
                image.convert('RGB').save(buffer, format='JPEG', quality=95)
                return buffer.getvalue()
                
            return image_data

        except Exception as e:
            self.logger.error(f"Image validation failed: {str(e)}")
            return None

    def _upload_poster(self, artist, image_url, source="unknown"):
        """Upload poster using direct upload method."""
        try:
            self.logger.info(f"Starting poster upload for {artist.title} from {source}")
            self.logger.debug(f"Image URL: {image_url}")
            
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Validate and potentially convert image
            image_data = self._validate_image(response.content)
            if not image_data:
                self.logger.error("Failed to validate/convert image")
                return False
            
            # Get the upload URL from Plex
            upload_url = f"{self.server._baseurl}/library/metadata/{artist.ratingKey}/posters"
            headers = {
                'X-Plex-Token': self.server._token,
                'Accept': 'application/json',
                'Content-Type': 'image/jpeg'
            }
            
            self.logger.debug(f"Uploading to Plex URL: {upload_url}")
            
            # Try direct upload first
            try:
                upload_response = requests.post(
                    upload_url,
                    data=image_data,  # Send raw image data
                    headers=headers
                )
                upload_response.raise_for_status()
            except Exception as e:
                self.logger.warning(f"Direct upload failed, trying multipart: {str(e)}")
                # Try multipart upload as fallback
                files = {'file': ('poster.jpg', image_data, 'image/jpeg')}
                upload_response = requests.post(upload_url, headers=headers, files=files)
                upload_response.raise_for_status()
            
            self.logger.debug(f"Upload response status: {upload_response.status_code}")
            self.logger.debug(f"Upload response content: {upload_response.text[:200]}")
            
            # Force refresh and verify
            artist.refresh()
            time.sleep(2)  # Give Plex time to process the image
            artist.reload()
            
            # Verify the image is actually accessible
            if artist.thumb:
                try:
                    # Try to download the new thumb to verify it's valid
                    verify_response = requests.get(artist.thumbUrl)
                    verify_response.raise_for_status()
                    if len(verify_response.content) > 0:
                        self.logger.info(f"Successfully verified thumb update for {artist.title}")
                        return True
                    else:
                        self.logger.warning(f"Thumb URL exists but returns no content for {artist.title}")
                        return False
                except Exception as e:
                    self.logger.error(f"Failed to verify new thumb: {str(e)}")
                    return False
            else:
                self.logger.warning(f"Upload appeared successful but thumb not updated for {artist.title}")
                return False
                
        except Exception as e:
            self.logger.error(f"Direct upload failed for {artist.title} from {source}: {str(e)}")
            return False

    def _verify_thumb(self, artist):
        """Verify that the artist's thumb is actually valid and usable."""
        if not artist.thumb:
            self.logger.debug(f"No thumb exists for {artist.title}")
            return False
        
        try:
            from PIL import Image
            import io
            
            # Try to download the current thumb
            response = requests.get(artist.thumbUrl, timeout=5)
            response.raise_for_status()
            
            # Log the content type and size
            content_type = response.headers.get('content-type', 'unknown')
            content_size = len(response.content)
            self.logger.debug(f"Thumb check for {artist.title}: Type={content_type}, Size={content_size} bytes")

            # If image is too small, it's probably invalid
            if content_size < 1000:  # Less than 1KB is suspicious
                self.logger.warning(f"Thumb exists but is suspiciously small for {artist.title} ({content_size} bytes)")
                return False

            # Try to open and validate the image
            try:
                image = Image.open(io.BytesIO(response.content))
                
                # Check image format
                format = image.format
                if format not in ['JPEG', 'PNG']:
                    self.logger.warning(f"Invalid image format for {artist.title}: {format}")
                    return False

                # Check image dimensions
                width, height = image.size
                if width < 100 or height < 100:  # Arbitrary minimum size
                    self.logger.warning(f"Image too small for {artist.title}: {width}x{height}")
                    return False

                # Try to verify image data
                image.verify()
                self.logger.debug(f"Valid image found for {artist.title}: {format} {width}x{height}")
                return True

            except Exception as img_e:
                self.logger.warning(f"Invalid image data for {artist.title}: {str(img_e)}")
                return False

        except Exception as e:
            self.logger.warning(f"Failed to verify existing thumb for {artist.title}: {str(e)}")
            return False

    def needs_processing(self, artist):
        """Check if an artist needs processing."""
        has_valid_thumb = self._verify_thumb(artist)
        existing_genres = set(artist.genres if artist.genres else [])
        
        self.logger.info(f"Checking processing needs for {artist.title}")
        self.logger.info(f"Current thumb status: {'Valid' if has_valid_thumb else 'Invalid/Missing'}")
        self.logger.info(f"Current genres: {existing_genres}")
        self.logger.info(f"Needs processing: No genres")

        return True
        

    def update_artist_metadata(self, artist, spotify_data):
        """Update artist metadata with Spotify information."""
        try:
            if not spotify_data:
                self.logger.error("No Spotify data provided")
                return False

            changes_needed = False
            changes_made = False
            self.logger.info(f"Starting metadata update for {artist.title}")
            
            # Check genres
            try:
                existing_genres = set(artist.genres if artist.genres else [])
                spotify_genres = set(spotify_data.get('genres', []))
                album_genres = set()
                
                self.logger.info(f"Existing genres: {existing_genres}")
                self.logger.info(f"Spotify genres: {spotify_genres}")
                
                for album in artist.albums():
                    if album.genres:
                        album_genres.update(album.genres)
                
                self.logger.info(f"Album genres: {album_genres}")

                # Combine all genres
                all_genres = existing_genres.union(spotify_genres, album_genres)
                
                # Check if we actually need to update genres
                if not existing_genres and all_genres:
                    self.logger.info(f"Artist has no genres, update needed")
                    changes_needed = True
                elif all_genres != existing_genres:
                    self.logger.info(f"New genres available, update needed")
                    changes_needed = True
                else:
                    self.logger.info(f"No genre updates needed - already has correct genres")

                if changes_needed:
                    genres_to_set = list(all_genres) if all_genres else ['Unknown']
                    self.logger.info(f"Attempting to set genres to: {genres_to_set}")
                    artist.addGenre(genres_to_set)
                    artist.reload()
                    changes_made = True
                    self.logger.info(f"Successfully updated genres")

            except Exception as e:
                self.logger.error(f"Error updating genres for {artist.title}: {str(e)}")

            # Check if poster update is needed
            if not self._verify_thumb(artist):
                self.logger.info(f"Artist needs poster update (invalid or missing)")
                changes_needed = True
                
                poster_updated = False
                # Try Spotify image first
                if spotify_data.get('images'):
                    try:
                        largest_image = max(spotify_data['images'], key=lambda x: x['width'] * x['height'])
                        self.logger.info(f"Found Spotify image: {largest_image['url']}")
                        self.logger.debug(f"Image dimensions: {largest_image['width']}x{largest_image['height']}")
                        
                        if self._upload_poster(artist, largest_image['url'], source="Spotify"):
                            poster_updated = True
                            changes_made = True
                            self.logger.info(f"Successfully updated poster from Spotify")
                    except Exception as e:
                        self.logger.error(f"Error uploading Spotify image: {str(e)}")

                # If Spotify image failed, try album art
                if not poster_updated:
                    try:
                        albums = artist.albums()
                        if albums:
                            # Sort albums by newest first (might have better quality art)
                            sorted_albums = sorted(albums, key=lambda x: x.year if x.year else 0, reverse=True)
                            for album in sorted_albums:
                                if album.thumb:
                                    self.logger.info(f"Attempting to use album art from: {album.title} ({album.year if album.year else 'Unknown year'})")
                                    if self._upload_poster(artist, album.thumbUrl, source=f"Album: {album.title}"):
                                        changes_made = True
                                        self.logger.info(f"Successfully set album art as artist poster")
                                        break
                    except Exception as e:
                        self.logger.error(f"Error setting album art as poster: {str(e)}")
            else:
                self.logger.info(f"No poster update needed - has valid poster")

            # Final status
            if not changes_needed:
                self.logger.info(f"No updates needed for {artist.title} - already up to date")
                return True
            elif changes_made:
                self.logger.info(f"Successfully made needed updates for {artist.title}")
                return True
            else:
                self.logger.warning(f"Updates were needed but could not be made for {artist.title}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to update metadata for {artist.title}: {str(e)}")
            return False