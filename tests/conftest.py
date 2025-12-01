"""
Configuration partagée pour pytest.
"""
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_path():
    """Retourne le chemin du projet."""
    return Path(__file__).parent.parent



