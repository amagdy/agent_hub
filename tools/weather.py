class Weather:
    def __init__(self, date: str):
        """
        {
            "description": "A class to get weather information for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for which to get the weather information, in YYYY-MM-DD format."
                    }
                },
                "required": ["date"]
            }
        }
        """
        self.date = date

    def get_temperature(self, location: str) -> str:
        """
        {
            "description": "Get the current temperature for a given location.", 
            "parameters": {
                "type": "object", 
                "properties": {
                    "location": {
                        "type": "string", 
                        "description": "The city and state, e.g. New York, NY"
                    }
                }, 
                "required": [
                    "location"
                ]
            }
        }
        """
        return f"25°C"

    def get_wind_speed(self, location: str) -> str:
        """
        {
            "description": "Get the current wind speed for a given location.", 
            "parameters": {
                "type": "object", 
                "properties": {
                    "location": {
                        "type": "string", 
                        "description": "The city and state, e.g. Seattle, WA"
                    }
                }, 
                "required": [
                    "location"
                ]
            }   
        }
        """
        return f"25 km/h"