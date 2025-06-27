import os
from dotenv import load_dotenv
import requests
import json
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def create_weather_service() -> Tuple[requests.Session, str]:
    """
    To create a weather service instance with the provided API key and base URL.
    """
    load_dotenv()
    api_key = os.getenv("ACCUWEATHER_API_KEY")
    base_url = "http://dataservice.accuweather.com"
    session = requests.Session()
    # session.headers.update({"Accept": "application/json"})
    
    return api_key, base_url, session
    
def get_current_location() -> Optional[Dict]:
    api_key, base_url, session = create_weather_service()
    try:
        url = f"{base_url}/locations/v1/cities/ipaddress"
        params = {"apikey": api_key}
        
        response = session.get(url, params=params)
        response.raise_for_status()
        
        location_data = response.json()
        return {
            "key": location_data.get("Key"),
            "name": location_data.get("LocalizedName"),
            "country": location_data.get("Country", {}).get("LocalizedName"),
            "region": location_data.get("AdministrativeArea", {}).get("LocalizedName"),
            "coordinates": {
                "latitude": location_data.get("GeoPosition", {}).get("Latitude"),
                "longitude": location_data.get("GeoPosition", {}).get("Longitude")
            }
        }
    except requests.RequestException as e:
        print(f"[WEATHER] Error getting current location: {e}")
        return None

def search_location(query: str) -> Optional[List[Dict]]:
    api_key, base_url, session = create_weather_service()
    try:
        url = f"{base_url}/locations/v1/cities/search"
        params = {
            "apikey": api_key,
            "q": query
        }
        
        response = session.get(url, params=params)
        response.raise_for_status()
        
        locations = response.json()
        return [
            {
                "key": loc.get("Key"),
                "name": loc.get("LocalizedName"),
                "country": loc.get("Country", {}).get("LocalizedName"),
                "region": loc.get("AdministrativeArea", {}).get("LocalizedName"),
                "coordinates": {
                    "latitude": loc.get("GeoPosition", {}).get("Latitude"),
                    "longitude": loc.get("GeoPosition", {}).get("Longitude")
                }
            }
            for loc in locations
        ]
    except requests.RequestException as e:
        print(f"[WEATHER] Error searching location: {e}")
        return None

def get_weather_for_location(location: str) -> Optional[Dict]:
    api_key, base_url, session = create_weather_service()

    if not location:
        logger.warning("No location provided for weather data, returning current location weather")
        location = get_current_location()
        if not location:
            return "[ERROR] Could not determine current location"
        location_key = location.get("key")

    else:
        location = search_location(location)
        if not location or len(location) == 0:
            return "[ERROR] No location found for the provided query"
        location_key = location[0].get("key")

    try:
        url = f"{base_url}/currentconditions/v1/{location_key}"
        params = {
            "apikey": api_key,
            "details": "true"
        }
        
        response = session.get(url, params=params)
        response.raise_for_status()
        
        weather_data = response.json()[0]
        
        return {
            "temperature": {
                "celsius": weather_data.get("Temperature", {}).get("Metric", {}).get("Value"),
                "fahrenheit": weather_data.get("Temperature", {}).get("Imperial", {}).get("Value")
            },
            "weather_text": weather_data.get("WeatherText"),
            "weather_icon": weather_data.get("WeatherIcon"),
            "humidity": weather_data.get("RelativeHumidity"),
            "wind": {
                "speed_kmh": weather_data.get("Wind", {}).get("Speed", {}).get("Metric", {}).get("Value"),
                "speed_mph": weather_data.get("Wind", {}).get("Speed", {}).get("Imperial", {}).get("Value"),
                "direction": weather_data.get("Wind", {}).get("Direction", {}).get("Localized")
            },
            "pressure": {
                "mb": weather_data.get("Pressure", {}).get("Metric", {}).get("Value"),
                "inches": weather_data.get("Pressure", {}).get("Imperial", {}).get("Value")
            },
            "visibility": {
                "km": weather_data.get("Visibility", {}).get("Metric", {}).get("Value"),
                "miles": weather_data.get("Visibility", {}).get("Imperial", {}).get("Value")
            },
            "uv_index": weather_data.get("UVIndex"),
            "observation_time": weather_data.get("LocalObservationDateTime")
        }
    except requests.RequestException as e:
        print(f"Error getting weather data: {e}")
        return None

def get_weather_forecast(location: str, days: int = 1) -> Optional[List[Dict]]:
    api_key, base_url, session = create_weather_service()

    if not location:
        logger.warning("No location provided for weather data, returning current location weather")
        location = get_current_location()
        if not location:
            return "[ERROR] Could not determine current location"
        location_key = location.get("key")

    else:
        location = search_location(location)
        if not location or len(location) == 0:
            return "[ERROR] No location found for the provided query"
        location_key = location[0].get("key")

    try:
        if days == 1:
            endpoint = "1day"
        elif days <= 5:
            endpoint = "5day"
        elif days <= 10:
            endpoint = "10day"
        else:
            endpoint = "15day"
        
        url = f"{base_url}/forecasts/v1/daily/{endpoint}/{location_key}"
        params = {
            "apikey": api_key,
            "details": "true",
            "metric": "true"
        }
        
        response = session.get(url, params=params)
        response.raise_for_status()
        
        forecast_data = response.json()
        daily_forecasts = forecast_data.get("DailyForecasts", [])
        
        forecast_list = []
        for day in daily_forecasts[:days]:
            forecast_list.append({
                "date": day.get("Date"),
                "temperature": {
                    "min_celsius": day.get("Temperature", {}).get("Minimum", {}).get("Value"),
                    "max_celsius": day.get("Temperature", {}).get("Maximum", {}).get("Value"),
                    "min_fahrenheit": _celsius_to_fahrenheit(
                        day.get("Temperature", {}).get("Minimum", {}).get("Value")
                    ),
                    "max_fahrenheit": _celsius_to_fahrenheit(
                        day.get("Temperature", {}).get("Maximum", {}).get("Value")
                    )
                },
                "day": {
                    "weather_text": day.get("Day", {}).get("IconPhrase"),
                    "weather_icon": day.get("Day", {}).get("Icon"),
                    "precipitation_probability": day.get("Day", {}).get("PrecipitationProbability"),
                    "wind_speed_kmh": day.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value")
                },
                "night": {
                    "weather_text": day.get("Night", {}).get("IconPhrase"),
                    "weather_icon": day.get("Night", {}).get("Icon"),
                    "precipitation_probability": day.get("Night", {}).get("PrecipitationProbability"),
                    "wind_speed_kmh": day.get("Night", {}).get("Wind", {}).get("Speed", {}).get("Value")
                }
            })
        
        return forecast_list
    except requests.RequestException as e:
        print(f"Error getting forecast data: {e}")
        return None

def _celsius_to_fahrenheit(celsius: Optional[float]) -> Optional[float]:
    """Convert Celsius to Fahrenheit"""
    if celsius is None:
        return None
    return round((celsius * 9/5) + 32, 1)
    
def weather_manager(args: dict):
    """Main weather control function"""
    
    service_type = args.get("type")

    if service_type == "get_current_location":
        try:
            return get_current_location()
        except Exception as e:
            return f"[ERROR] Failed to get current location: {e}"

    elif service_type == "search_location":
        try:
            return search_location(args.get("query", ""))
        except Exception as e:
            return f"[ERROR] Failed to search location: {e}"

    elif service_type == "get_weather_for_location":
        location = args.get("location")
        return get_weather_for_location(location)

    elif service_type == "get_weather_forecast":
        location = args.get("location")
        days = args.get("days", 1)
        if not location:
            return "[ERROR] Missing location key for weather forecast"
        if not isinstance(days, int) or days < 1 or days > 15:
            return "[ERROR] Days must be an integer between 1 and 15"
        return get_weather_forecast(location, days)
    

# if __name__ == "__main__":
#     print ("AccuWeather Service Module")

#     args1 = { "type": "get_current_location"}
#     args2 = { "type": "search_location", "query": "Vietnam" }
#     args3 = { "type": "get_weather_for_location", "location": "" }
#     args4 = { "type": "get_weather_forecast", "location": "Kashmir", "days": 1 } 

    # print(weather_manager(args1))
    # print ("----------------------------------------")
    # print(weather_manager(args2))
    # print ("----------------------------------------")
    # print(weather_manager(args3))
    # print ("----------------------------------------")
    # print(weather_manager(args4))