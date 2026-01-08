# Polar-Garmin Sync

A high-performance Python application that synchronizes sport activities from Polar.com to Garmin Connect.

> [!NOTE]
> This application has been optimized with modern **AsyncIO** and **Pydantic** for fast, reliable, and concurrent synchronization.

## Features

- **High-Performance Sync**: Uses `asyncio` and `httpx` to process multiple activities in parallel.
- **Robust Validation**: Powered by `Pydantic` for strict data validation and type safety.
- **OAuth Authentication**: Secure authentication for both Polar and Garmin services.
- **Duplicate Detection**: Tracks synced activities in a SQLite database to prevent duplicates.
- **Activity Type Mapping**: Smartly maps Polar sports to Garmin equivalents.
- **Resiliency**: Automatic retry mechanism for failed network operations.
- **Modern Stack**: Built with Python 3.12+ features.

## Prerequisites

- **Python 3.12** or higher
- Polar AccessLink API credentials ([Register here](https://admin.polaraccesslink.com/))
- Garmin Connect account

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/polar-garmin-sync.git
   cd polar-garmin-sync
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   Copy `.env.example` to `.env` and fill in your credentials.
   ```bash
   # On Windows
   copy .env.example .env
   # On macOS/Linux
   cp .env.example .env
   ```

## Configuration

Edit the `.env` file with your credentials:

```env
POLAR_CLIENT_ID=your_polar_client_id
POLAR_CLIENT_SECRET=your_polar_client_secret
GARMIN_EMAIL=your_garmin_email
GARMIN_PASSWORD=your_garmin_password
```

## Usage

### First-time Setup

Run the authorization flow to connect your Polar account:

```bash
python -m src.main --authorize
```

This will open a browser window for Polar OAuth authentication.

### Sync Activities

To sync all new activities from Polar to Garmin:

```bash
python -m src.main --sync
```

Failed syncs are automatically tracked and can be retried later.

### Sync Statistics

View detailed statistics about your sync history:

```bash
python -m src.main --stats
```

### Options

- `--authorize`: Run Polar OAuth authorization flow
- `--sync`: Sync new activities from Polar to Garmin
- `--retry-failed`: Retry previously failed sync attempts
- `--dry-run`: Preview what would be synced without making changes
- `--stats`: Show sync statistics
- `--verbose`: Enable verbose logging

## Technical Architecture

The application uses a modern asynchronous architecture:

- **Entry Point**: `src/main.py` uses `asyncio.run()` to bootstrap the event loop.
- **Network Layer**: `src/polar_client.py` uses `httpx.AsyncClient` for non-blocking API calls. `src/garmin_client.py` wraps `garth` in `asyncio.to_thread` to prevent blocking.
- **Concurrency**: `src/sync_manager.py` uses `asyncio.TaskGroup` to sync multiple activities simultaneously.
- **Data Models**: `src/models.py` uses `Pydantic` V2 for parsing and validation.

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## License

MIT License
