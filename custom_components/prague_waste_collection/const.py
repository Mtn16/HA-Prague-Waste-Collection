from enum import Enum

DOMAIN = "prague_waste_collection"
ATTR_STATION_ID = "station_id"
ATTR_CONTAINER_ID = "container_id"

class StationType(str, Enum):
    PUBLIC = "1"
    RESIDENTIAL = "2"

    @classmethod
    def choices(cls):
        return {
            cls.PUBLIC: "Veřejně přístupné (1)",
            cls.RESIDENTIAL: "Obyvatelé domu / uzavřené (2)",
        }