import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from src.core.database import SessionLocal
from src.models.source import Source


def seed_channels():
    channels = [
        {"name": "@XavierMitjana", "url": "https://www.youtube.com/@XavierMitjana"},
        {"name": "@SDESALVAJE", "url": "https://www.youtube.com/@SDESALVAJE"},
        {"name": "@BettaTech", "url": "https://www.youtube.com/@BettaTech"},
        {
            "name": "@la_inteligencia_artificial",
            "url": "https://www.youtube.com/@la_inteligencia_artificial",
        },
        {"name": "@PeladoNerd", "url": "https://www.youtube.com/@peladonerd"},
        {"name": "@mouredev", "url": "https://www.youtube.com/@mouredev"},
        {"name": "@victorroblesweb", "url": "https://www.youtube.com/@victorroblesweb"},
        {"name": "@HolaMundoDev", "url": "https://www.youtube.com/@HolaMundoDev"},
        {"name": "@midudev", "url": "https://www.youtube.com/@midudev"},
        {"name": "@CodelyTV", "url": "https://www.youtube.com/@CodelyTV"},
        {"name": "@javimanzanoo", "url": "https://www.youtube.com/@javimanzanoo"},
        {"name": "@InDevAlways", "url": "https://www.youtube.com/@InDevAlways"},
        {"name": "@iia", "url": "https://www.youtube.com/@iia"},
        {"name": "@alejavirivera", "url": "https://www.youtube.com/@alejavirivera"},
        {"name": "@maxmaxdata", "url": "https://www.youtube.com/@maxmaxdata"},
        {"name": "@RodrigoDeLaTorre-AI", "url": "https://www.youtube.com/@RodrigoDeLaTorre-AI"},
        {"name": "@pabloesdev", "url": "https://www.youtube.com/@pabloesdev"},
        {"name": "@FaztTech", "url": "https://www.youtube.com/@FaztTech"},
        {"name": "@MigueBaenaIA", "url": "https://www.youtube.com/@MigueBaenaIA"},
        {"name": "@javiergarzas", "url": "https://www.youtube.com/@javiergarzas"},
        {"name": "@CharlyAutomatiza", "url": "https://www.youtube.com/@CharlyAutomatiza"},
        {"name": "@CarlosAzaustre", "url": "https://www.youtube.com/@CarlosAzaustre"},
        {"name": "@AristiDevs", "url": "https://www.youtube.com/@AristiDevs"},
        {"name": "@gentlemanprogramming", "url": "https://www.youtube.com/@gentlemanprogramming"},
        {"name": "@freecodecampes", "url": "https://www.youtube.com/@freecodecampes"},
        {"name": "@kikopalomares", "url": "https://www.youtube.com/@kikopalomares"},
        {"name": "@xavidop", "url": "https://www.youtube.com/@xavidop"},
    ]

    db = SessionLocal()
    try:
        print(f"Starting seed of {len(channels)} channels...")
        added_count = 0
        skipped_count = 0

        for channel_data in channels:
            # Check if exists
            existing = db.query(Source).filter(Source.url == channel_data["url"]).first()
            if existing:
                print(f"Skipping {channel_data['name']} (already exists)")
                skipped_count += 1
                continue

            new_source = Source(
                name=channel_data["name"],
                url=channel_data["url"],
                source_type="youtube",
                active=True,
            )
            db.add(new_source)
            added_count += 1
            print(f"Added {channel_data['name']}")

        db.commit()
        print(f"\nFinished! Added: {added_count}, Skipped: {skipped_count}")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_channels()
