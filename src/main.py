import logging
from tqdm import tqdm
import time
from config_handler import ConfigHandler
from database_handler import DatabaseHandler
from plex_handler import PlexHandler
from spotify_handler import SpotifyHandler

def sanitize_text(text):
    """Sanitize text for console output"""
    try:
        return text.encode('ascii', 'replace').decode('ascii')
    except:
        return '[Complex Name]'

def setup_logging(config):
    logger = logging.getLogger('PlexMusicEnricher')
    logger.setLevel(logging.INFO)

    # Create custom formatter that sanitizes messages
    class SanitizedFormatter(logging.Formatter):
        def format(self, record):
            record.msg = sanitize_text(str(record.msg))
            return super().format(record)

    # File handler with sanitized formatter
    file_handler = logging.FileHandler(config.get_logging_config()['path'], encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = SanitizedFormatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

def main():
    # Load configuration
    config = ConfigHandler()
    
    # Setup logger
    logger = setup_logging(config)
    
    try:
        # Initialize handlers quietly
        db_handler = DatabaseHandler(config.get_database_config()['path'])
        plex_handler = PlexHandler(**config.get_plex_config())
        spotify_handler = SpotifyHandler(**config.get_spotify_config())
        
        # Get all artists
        artists = plex_handler.get_all_artists()
        total_artists = len(artists)
        
        # Setup progress bar with custom format
        pbar = tqdm(
            total=total_artists,
            bar_format='{percentage:3.0f}% |{bar:20}| {n_fmt}/{total_fmt} '
                      '[{elapsed}<{remaining}, {rate_fmt}] {desc}',
            ncols=100
        )
        
        # Process artists in batches
        batch_size = 5
        for i in range(0, len(artists), batch_size):
            batch = artists[i:i + batch_size]
            
            # Process batch
            processed = plex_handler.process_artist_batch(batch, db_handler, spotify_handler)
            
            # Update progress bar with current artist (sanitized)
            if batch:
                current_artist = sanitize_text(batch[0].title)[:30]
                pbar.set_description(f"Current: {current_artist:<30}")
            
            # Update progress
            pbar.update(len(batch))
            
            # Rate limiting
            time.sleep(0.5)
        
        pbar.close()
        
        # Show final statistics
        total, successful, failed = db_handler.get_processing_stats()
        print(f"\nCompleted: {successful} successful, {failed} failed")
        
    except Exception as e:
        logger.error(f"Application error: {sanitize_text(str(e))}")
        raise

if __name__ == "__main__":
    main()