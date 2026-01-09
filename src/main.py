"""Main entry point for Polar-Garmin Sync application."""

import argparse
import logging
import sys
import asyncio

from .config.settings import settings
from .sync_manager import SyncManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def setup_argparser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Sync sport activities from Polar.com to Garmin Connect",
        prog="polar-garmin-sync",
    )
    
    parser.add_argument(
        "--authorize",
        action="store_true",
        help="Run Polar OAuth authorization flow",
    )
    
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync new activities from Polar to Garmin",
    )
    
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry previously failed sync operations",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be synced without making changes",
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show sync statistics",
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser


async def main_async() -> int:
    """Async main entry point."""
    parser = setup_argparser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    errors = settings.validate()
    
    if errors and not args.authorize:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease set up your .env file. See .env.example for reference.")
        return 1
    
    # Create sync manager
    sync_manager = SyncManager(settings)
    
    # Handle commands
    if args.authorize:
        logger.info("Starting Polar authorization...")
        # Authorize is synchronous in its current implementation (uses webbrowser + simple server)
        # But we might have some async internals if we changed it.
        # Currently polar.authorize() is synchronous based on previous refactor?
        # Let's check polar_client.py. authorize() is sync.
        # Let's check polar_client.py. authorize() is sync.
        if await sync_manager.polar.authorize():
            print("\n✓ Authorization successful!")
            print("You can now sync activities with --sync")
            return 0
        else:
            print("\n✗ Authorization failed!")
            return 1
    
    if args.stats:
        stats = sync_manager.get_stats()
        print("\n=== Sync Statistics ===")
        print(f"Total activities: {stats['total']}")
        print(f"  Successful: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Skipped: {stats['skipped']}")
        return 0
    
    if args.sync:
        logger.info("Starting activity sync...")
        result = await sync_manager.sync_all(dry_run=args.dry_run)
        
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}{result}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")
        
        return 0 if result.success else 1
    
    if args.retry_failed:
        logger.info("Retrying failed syncs...")
        result = await sync_manager.retry_failed()
        
        print(f"\n{result}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")
        
        return 0 if result.success else 1
    
    # No command specified
    parser.print_help()
    return 0


def main() -> int:
    """Entry point."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
