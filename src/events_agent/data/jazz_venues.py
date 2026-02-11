"""NYC Jazz Venue Index.

Major jazz venues in NYC with location and metadata.
This serves as reference data for venue-based crawling and filtering.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class JazzVenue:
    """Jazz venue data structure."""
    name: str
    address: str
    city: str
    state: str
    neighborhood: str
    venue_type: str  # club, bar, concert-hall, restaurant
    website: Optional[str] = None
    capacity: Optional[int] = None
    notes: Optional[str] = None


# Major NYC Jazz Venues
NYC_JAZZ_VENUES = [
    # Greenwich Village
    JazzVenue(
        name="Village Vanguard",
        address="178 7th Ave S, New York, NY 10014",
        city="New York",
        state="NY",
        neighborhood="Greenwich Village",
        venue_type="club",
        website="https://villagevanguard.com",
        capacity=123,
        notes="Historic jazz club, opened 1935"
    ),
    JazzVenue(
        name="Blue Note Jazz Club",
        address="131 W 3rd St, New York, NY 10012",
        city="New York",
        state="NY",
        neighborhood="Greenwich Village",
        venue_type="club",
        website="https://bluenotejazz.com",
        capacity=200,
        notes="Premier jazz venue"
    ),
    JazzVenue(
        name="Smalls Jazz Club",
        address="183 W 10th St, New York, NY 10014",
        city="New York",
        state="NY",
        neighborhood="Greenwich Village",
        venue_type="club",
        website="https://smallslive.com",
        capacity=60,
        notes="Intimate basement club"
    ),
    JazzVenue(
        name="Mezzrow",
        address="163 W 10th St, New York, NY 10014",
        city="New York",
        state="NY",
        neighborhood="Greenwich Village",
        venue_type="club",
        website="https://mezzrow.com",
        capacity=60,
        notes="Sister venue to Smalls"
    ),
    
    # Midtown
    JazzVenue(
        name="Birdland Jazz Club",
        address="315 W 44th St, New York, NY 10036",
        city="New York",
        state="NY",
        neighborhood="Midtown",
        venue_type="club",
        website="https://birdlandjazz.com",
        capacity=160,
        notes="Classic jazz club"
    ),
    JazzVenue(
        name="Iridium Jazz Club",
        address="1650 Broadway, New York, NY 10019",
        city="New York",
        state="NY",
        neighborhood="Midtown",
        venue_type="club",
        website="https://theiridium.com",
        capacity=180,
    ),
    JazzVenue(
        name="Dizzy's Club",
        address="10 Columbus Circle, New York, NY 10019",
        city="New York",
        state="NY",
        neighborhood="Columbus Circle",
        venue_type="concert-hall",
        website="https://jazz.org/dizzys",
        capacity=140,
        notes="Part of Jazz at Lincoln Center"
    ),
    
    # Harlem
    JazzVenue(
        name="Minton's Playhouse",
        address="206 W 118th St, New York, NY 10026",
        city="New York",
        state="NY",
        neighborhood="Harlem",
        venue_type="club",
        website="https://mintonsharlem.com",
        notes="Historic bebop birthplace"
    ),
    JazzVenue(
        name="Bill's Place",
        address="148 W 133rd St, New York, NY 10030",
        city="New York",
        state="NY",
        neighborhood="Harlem",
        venue_type="club",
        capacity=40,
        notes="Speakeasy-style venue"
    ),
    JazzVenue(
        name="The Django",
        address="2 Avenue of the Americas, New York, NY 10013",
        city="New York",
        state="NY",
        neighborhood="Tribeca",
        venue_type="club",
        website="https://thedjangonyc.com",
        capacity=80,
        notes="Modern jazz lounge"
    ),
    
    # Brooklyn
    JazzVenue(
        name="Somethin' Jazz Club",
        address="212 E 52nd St, New York, NY 10022",
        city="New York",
        state="NY",
        neighborhood="Midtown East",
        venue_type="club",
        capacity=80,
    ),
    JazzVenue(
        name="Zinc Bar",
        address="82 W 3rd St, New York, NY 10012",
        city="New York",
        state="NY",
        neighborhood="Greenwich Village",
        venue_type="bar",
        website="https://zincbar.com",
        capacity=100,
        notes="Latin jazz focus"
    ),
    
    # Multi-genre venues with frequent jazz
    JazzVenue(
        name="The Jazz Gallery",
        address="1160 Broadway, New York, NY 10001",
        city="New York",
        state="NY",
        neighborhood="Flatiron",
        venue_type="gallery",
        website="https://jazzgallery.org",
        capacity=120,
        notes="Nonprofit, emerging artists"
    ),
    JazzVenue(
        name="Roulette Intermedium",
        address="509 Atlantic Ave, Brooklyn, NY 11217",
        city="Brooklyn",
        state="NY",
        neighborhood="Boerum Hill",
        venue_type="concert-hall",
        website="https://roulette.org",
        capacity=400,
        notes="Experimental music and jazz"
    ),
    JazzVenue(
        name="Nublu",
        address="151 Avenue C, New York, NY 10009",
        city="New York",
        state="NY",
        neighborhood="East Village",
        venue_type="club",
        website="https://nublu.net",
        capacity=80,
        notes="Jazz and electronic fusion"
    ),
]


# NYC neighborhoods with high jazz venue concentration
JAZZ_NEIGHBORHOODS = {
    "Greenwich Village": ["Village Vanguard", "Blue Note", "Smalls", "Mezzrow", "Zinc Bar"],
    "Midtown": ["Birdland", "Iridium", "Somethin' Jazz Club"],
    "Harlem": ["Minton's Playhouse", "Bill's Place"],
    "East Village": ["Nublu"],
    "Tribeca": ["The Django"],
    "Flatiron": ["The Jazz Gallery"],
    "Brooklyn": ["Roulette"],
}


def get_venue_by_name(name: str) -> Optional[JazzVenue]:
    """
    Look up venue by name (case-insensitive).
    
    Args:
        name: Venue name to search for.
        
    Returns:
        JazzVenue object or None if not found.
    """
    if not name or not str(name).strip():
        return None
    name_lower = name.lower().strip()
    for venue in NYC_JAZZ_VENUES:
        if name_lower in venue.name.lower():
            return venue
    return None


def get_venues_by_neighborhood(neighborhood: str) -> List[JazzVenue]:
    """
    Get all venues in a neighborhood.
    
    Args:
        neighborhood: Neighborhood name.
        
    Returns:
        List of JazzVenue objects.
    """
    return [v for v in NYC_JAZZ_VENUES if v.neighborhood.lower() == neighborhood.lower()]


def get_all_venue_names() -> List[str]:
    """Get list of all venue names."""
    return [v.name for v in NYC_JAZZ_VENUES]


def get_venue_neighborhoods() -> List[str]:
    """Get list of all neighborhoods with jazz venues."""
    return list(JAZZ_NEIGHBORHOODS.keys())


def is_known_jazz_venue(venue_name: str) -> bool:
    """
    Check if a venue name matches a known jazz venue.
    
    Args:
        venue_name: Venue name to check.
        
    Returns:
        True if venue is in the index.
    """
    return get_venue_by_name(venue_name) is not None
