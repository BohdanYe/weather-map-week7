from django.core.management.base import BaseCommand
from weathermap.models import City


CITIES = [
    ("London", "United Kingdom", 51.5074, -0.1278),
    ("Paris", "France", 48.8566, 2.3522),
    ("New York", "United States", 40.7128, -74.0060),
    ("Tokyo", "Japan", 35.6762, 139.6503),
    ("Sydney", "Australia", -33.8688, 151.2093),
    ("Dubai", "UAE", 25.2048, 55.2708),
    ("São Paulo", "Brazil", -23.5505, -46.6333),
    ("Mumbai", "India", 19.0760, 72.8777),
    ("Cairo", "Egypt", 30.0444, 31.2357),
    ("Moscow", "Russia", 55.7558, 37.6173),
]


class Command(BaseCommand):
    help = "Populate the database with world cities"

    def handle(self, *args, **options):
        created_count = 0

        for name, country, latitude, longitude in CITIES:
            _, created = City.objects.update_or_create(
                name=name,
                country=country,
                defaults={
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            created_count += int(created)

        total = City.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} cities. "
                f"Total cities in database: {total}"
            )
        )