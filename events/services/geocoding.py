"""
Geocoding service to convert addresses to latitude/longitude coordinates.
"""
import requests
from typing import Optional, Tuple
from decouple import config


class GeocodingService:
    """Service to geocode addresses using Google Maps Geocoding API."""
    
    def __init__(self):
        """Initialize the geocoding service with API key."""
        self.api_key = config('GOOGLE_MAPS_API_KEY', default='')
        self.base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert an address to latitude and longitude coordinates.
        
        Args:
            address: The address string to geocode
            
        Returns:
            Tuple of (latitude, longitude) if successful, None otherwise
        """
        if not address or not address.strip():
            return None
        
        if not self.api_key or self.api_key == 'your-google-maps-api-key-here':
            # No API key configured, skip geocoding
            return None
        
        try:
            params = {
                'address': address,
                'key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                return (lat, lng)
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Geocoding error for '{address}': {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error parsing geocoding response for '{address}': {e}")
            return None
    
    def is_configured(self) -> bool:
        """Check if the geocoding service is properly configured."""
        return bool(self.api_key and self.api_key != 'your-google-maps-api-key-here')

