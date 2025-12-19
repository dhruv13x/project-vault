import os
import re

DATABASE_MARKERS = {
    "Postgres/SQLAlchemy": ["alembic.ini", "migrations/"],
    "Django": ["manage.py"],
    "Prisma/Node": ["schema.prisma", "prisma/"],
    "MySQL/General": ["mysql-init.sql"],
}

def detect_database_markers(directory: str) -> list[str]:
    """
    Scans the given directory for database-related markers.
    Returns a list of detected markers (friendly names).
    """
    detected = []
    
    # Check for direct file/folder markers
    for category, markers in DATABASE_MARKERS.items():
        for marker in markers:
            path = os.path.join(directory, marker)
            if os.path.exists(path):
                detected.append(marker)
                break # Move to next category if one marker found

    # Check docker-compose.yml for database images
    docker_compose = os.path.join(directory, "docker-compose.yml")
    if os.path.exists(docker_compose):
        try:
            with open(docker_compose, "r") as f:
                content = f.read()
                if re.search(r"image:.*(postgres|mysql|mariadb|postgis)", content, re.IGNORECASE):
                    detected.append("docker-compose.yml (db image)")
        except Exception:
            pass

    return detected
