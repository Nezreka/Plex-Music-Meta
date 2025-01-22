# src/main.py
import logging
from tqdm import tqdm
import time
from config_handler import ConfigHandler
from database_handler import DatabaseHandler
from plex_handler import PlexHandler
from spotify_handler import SpotifyHandler

def setup_logging(config):
    logger = logging.getLogger('PlexMusicEnricher')
    logger.setLevel(logging.DEBUG)

    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with DEBUG level
    file_handler = logging.FileHandler(config.get_logging_config()['path'])
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

def main():
    # Load configuration
    config = ConfigHandler()
    
    # Setup logger
    logger = setup_logging(config)
    
    try:
        # Initialize handlers
        logger.info("Initializing handlers...")
        db_handler = DatabaseHandler(config.get_database_config()['path'])
        plex_handler = PlexHandler(**config.get_plex_config())
        spotify_handler = SpotifyHandler(**config.get_spotify_config())
        
        # Get all artists
        artists = plex_handler.get_all_artists()
        logger.info(f"Found {len(artists)} artists in Plex library")
        
        # Setup progress bar
        pbar = tqdm(total=len(artists), desc="Processing artists")
        
        for artist in artists:
            current_desc = f"Processing {artist.title:<30}"
            pbar.set_description(current_desc)
            logger.info(f"\n{'='*50}\nProcessing artist: {artist.title}")
            
            try:
                # Skip if already processed
                needs_processing = plex_handler.needs_processing(artist)
                if db_handler.is_artist_processed(artist.ratingKey):
                    logger.debug(f"Skipping {artist.title} - already processed")
                    pbar.update(1)
                    continue
                
                # Check if processing needed
                if not needs_processing:
                    logger.info(f"No processing needed for {artist.title}")
                    db_handler.mark_artist_processed(
                        artist.ratingKey,
                        artist.title,
                        success=True
                    )
                    pbar.update(1)
                    continue
                
                logger.info(f"Searching Spotify for {artist.title}")
                spotify_data = spotify_handler.search_artist(artist.title)
                
                if spotify_data:
                    logger.info(f"Found {artist.title} on Spotify, getting details...")
                    logger.debug(f"Spotify data: {spotify_data}")  # Add this line

                    details = spotify_handler.get_artist_details(spotify_data['spotify_id'])
                    if details:
                        spotify_data.update(details)
                        logger.debug(f"Combined Spotify data: {spotify_data}")
                    
                    success = plex_handler.update_artist_metadata(artist, spotify_data)
                    logger.info(f"Metadata update {'successful' if success else 'failed'} for {artist.title}")
                    
                    db_handler.mark_artist_processed(
                        artist.ratingKey,
                        artist.title,
                        spotify_id=spotify_data['spotify_id'],
                        success=success
                    )
                else:
                    logger.warning(f"Artist not found on Spotify: {artist.title}")
                    db_handler.mark_artist_processed(
                        artist.ratingKey,
                        artist.title,
                        success=False,
                        error_message="Not found on Spotify"
                    )
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing artist {artist.title}: {str(e)}")
                db_handler.mark_artist_processed(
                    artist.ratingKey,
                    artist.title,
                    success=False,
                    error_message=str(e)
                )
            
            finally:
                pbar.update(1)
        
        pbar.close()
        
        # Show final statistics
        total, successful, failed = db_handler.get_processing_stats()
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing completed. Total: {total}, Successful: {successful}, Failed: {failed}")
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()