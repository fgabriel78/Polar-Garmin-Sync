"""Activity type mapping between Polar and Garmin."""

from typing import Optional

# Mapping from Polar activity types to Garmin activity types
# Polar types: https://www.polar.com/accesslink-api/#activity-types
# Garmin types: Based on Garmin Connect activity categories

POLAR_TO_GARMIN_MAPPING: dict[str, str] = {
    # Running activities
    "RUNNING": "running",
    "JOGGING": "running",
    "ROAD_RUNNING": "running",
    "TRAIL_RUNNING": "trail_running",
    "TREADMILL_RUNNING": "treadmill_running",
    
    # Cycling activities
    "CYCLING": "cycling",
    "ROAD_BIKING": "cycling",
    "MOUNTAIN_BIKING": "mountain_biking",
    "INDOOR_CYCLING": "indoor_cycling",
    "SPINNING": "indoor_cycling",
    
    # Swimming activities
    "SWIMMING": "swimming",
    "POOL_SWIMMING": "lap_swimming",
    "OPEN_WATER_SWIMMING": "open_water_swimming",
    
    # Walking activities
    "WALKING": "walking",
    "HIKING": "hiking",
    "NORDIC_WALKING": "walking",
    
    # Gym and fitness
    "STRENGTH_TRAINING": "strength_training",
    "WEIGHT_TRAINING": "strength_training",
    "CIRCUIT_TRAINING": "strength_training",
    "CORE": "strength_training",
    "FLEXIBILITY": "yoga",
    "YOGA": "yoga",
    "PILATES": "pilates",
    "AEROBICS": "cardio",
    "FITNESS_CLASS": "cardio",
    "FUNCTIONAL_TRAINING": "strength_training",
    "BOOTCAMP": "cardio",
    
    # Winter sports
    "CROSS_COUNTRY_SKIING": "cross_country_skiing_classic",
    "DOWNHILL_SKIING": "resort_skiing",
    "SKIING": "resort_skiing",
    "SNOWBOARDING": "snowboarding",
    "ICE_SKATING": "skating",
    
    # Water sports
    "ROWING": "rowing",
    "INDOOR_ROWING": "indoor_rowing",
    "KAYAKING": "kayaking",
    "CANOEING": "kayaking",
    "STAND_UP_PADDLING": "stand_up_paddleboarding",
    "SURFING": "surfing",
    
    # Racket sports
    "TENNIS": "tennis",
    "BADMINTON": "badminton",
    "SQUASH": "squash",
    "TABLE_TENNIS": "table_tennis",
    "PADEL": "tennis",
    
    # Team sports
    "SOCCER": "soccer",
    "FOOTBALL": "football",
    "BASKETBALL": "basketball",
    "VOLLEYBALL": "volleyball",
    "HANDBALL": "handball",
    "ICE_HOCKEY": "ice_hockey",
    "FIELD_HOCKEY": "field_hockey",
    "RUGBY": "rugby",
    
    # Combat sports
    "MARTIAL_ARTS": "martial_arts",
    "BOXING": "boxing",
    "KICKBOXING": "kickboxing",
    "WRESTLING": "wrestling",
    
    # Other activities
    "GOLF": "golf",
    "DANCING": "dancing",
    "HORSE_RIDING": "horseback_riding",
    "CLIMBING": "climbing_indoor",
    "ELLIPTICAL": "elliptical",
    "STAIR_CLIMBING": "stair_climbing",
    "CROSSFIT": "crossfit",
    "TRIATHLON": "triathlon",
    "MULTISPORT": "multi_sport",
    
    # Generic
    "OTHER": "other",
    "OTHER_INDOOR": "other",
    "OTHER_OUTDOOR": "other",
}


def get_garmin_activity_type(polar_type: str, default: str = "other") -> str:
    """
    Get the Garmin activity type for a given Polar activity type.
    
    Args:
        polar_type: The Polar activity type string.
        default: Default activity type if no mapping is found.
    
    Returns:
        The corresponding Garmin activity type.
    """
    # Normalize the input
    normalized_type = polar_type.upper().replace(" ", "_").replace("-", "_")
    
    return POLAR_TO_GARMIN_MAPPING.get(normalized_type, default)


def get_available_polar_types() -> list[str]:
    """Get list of all mapped Polar activity types."""
    return sorted(POLAR_TO_GARMIN_MAPPING.keys())


def get_available_garmin_types() -> list[str]:
    """Get list of all unique Garmin activity types used in mapping."""
    return sorted(set(POLAR_TO_GARMIN_MAPPING.values()))
