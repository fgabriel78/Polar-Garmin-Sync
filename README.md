# Polar-Garmin Sync

A Python application that synchronizes sport activities from Polar.com to Garmin Connect.

## Features

- **OAuth Authentication**: Secure authentication for both Polar and Garmin services
- **Activity Sync**: Automatically sync activities from Polar to Garmin
- **Duplicate Detection**: Tracks synced activities to avoid duplicates
- **Activity Type Mapping**: Maps Polar activity types to Garmin equivalents
- **Retry Mechanism**: Automatic retry for failed sync attempts
- **Persistent Storage**: SQLite database for sync history

## Prerequisites

- Python 3.10 or higher
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
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
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

### Options

- `--authorize`: Run Polar OAuth authorization flow
- `--sync`: Sync new activities from Polar to Garmin
- `--retry-failed`: Retry previously failed sync attempts
- `--dry-run`: Preview what would be synced without making changes
- `--verbose`: Enable verbose logging

## Activity Type Mapping

The application maps Polar activity types to Garmin equivalents:

| Polar Type | Garmin Type |
|------------|-------------|
| RUNNING | running |
| CYCLING | cycling |
| SWIMMING | swimming |
| STRENGTH_TRAINING | strength_training |
| OTHER | other |

See `src/config/activity_mapping.py` for the complete mapping.

## Project Structure

```
polar-garmin-sync/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── polar_client.py      # Polar API client
│   ├── garmin_client.py     # Garmin Connect client
│   ├── sync_manager.py      # Sync orchestration
│   ├── database.py          # SQLite operations
│   ├── models.py            # Data models
│   └── config/
│       ├── __init__.py
│       ├── settings.py      # Configuration settings
│       └── activity_mapping.py  # Activity type mapping
├── tests/
│   └── ...
├── data/                    # Database and logs
├── requirements.txt
├── pyproject.toml
└── README.md
```

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
