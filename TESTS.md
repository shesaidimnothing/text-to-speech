# Guide des Tests

## Exécution des Tests avec JavaScript

Un script JavaScript est disponible pour exécuter les tests Python et afficher les résultats de manière formatée dans la console :

```bash
node run_tests.js
```

Pour exécuter un fichier de test spécifique :

```bash
node run_tests.js test_question_detector.py
node run_tests.js test_answer_generator.py
node run_tests.js test_transcription.py
node run_tests.js test_audio_capture.py
```

Ou utiliser npm :

```bash
npm test
npm run test:question
npm run test:answer
npm run test:transcription
npm run test:audio
```

Le script affiche les résultats avec des couleurs et un formatage clair dans la console du terminal.

## Installation des Dépendances de Test

```bash
pip install pytest pytest-mock
```

Ou pour installer toutes les dépendances de développement :

```bash
pip install pytest pytest-mock pytest-cov
```

## Structure des Tests

Les tests sont organisés dans le répertoire `tests/` :

```
tests/
├── __init__.py
├── conftest.py                    # Configuration partagée
├── test_question_detector.py      # Tests pour QuestionDetector
├── test_answer_generator.py      # Tests pour AnswerGenerator (avec mocking)
├── test_transcription.py          # Tests pour TranscriptionEngine (avec mocking)
└── test_audio_capture.py         # Tests pour AudioCapture (avec mocking)
```

## Commandes pour Exécuter les Tests

### Exécuter tous les tests

```bash
pytest
```

### Exécuter avec détails (verbose)

```bash
pytest -v
```

### Exécuter un fichier de test spécifique

```bash
pytest tests/test_question_detector.py
pytest tests/test_answer_generator.py
pytest tests/test_transcription.py
pytest tests/test_audio_capture.py
```

### Exécuter une classe de test spécifique

```bash
pytest tests/test_question_detector.py::TestQuestionDetector
```

### Exécuter un test spécifique

```bash
pytest tests/test_question_detector.py::TestQuestionDetector::test_detects_question_mark
```

### Exécuter avec couverture de code

```bash
pytest --cov=. --cov-report=term-missing
```

### Exécuter uniquement les tests rapides (exclure les tests lents)

```bash
pytest -m "not slow"
```

### Exécuter uniquement les tests unitaires

```bash
pytest -m unit
```

### Exécuter avec sortie détaillée en cas d'échec

```bash
pytest -vv
```

### Exécuter et arrêter au premier échec

```bash
pytest -x
```

### Exécuter les tests en parallèle (si pytest-xdist installé)

```bash
pip install pytest-xdist
pytest -n auto
```

## Types de Tests

### Tests Unitaires

Les tests unitaires testent chaque composant isolément avec mocking :

- **test_question_detector.py** : Tests de détection de questions
- **test_answer_generator.py** : Tests avec mocking d'Ollama API
- **test_transcription.py** : Tests avec mocking de Whisper
- **test_audio_capture.py** : Tests avec mocking de sounddevice

### Marqueurs de Tests

Les tests peuvent être marqués pour différentes catégories :

- `@pytest.mark.unit` : Tests unitaires
- `@pytest.mark.integration` : Tests d'intégration
- `@pytest.mark.slow` : Tests lents (nécessitent Whisper/Ollama)
- `@pytest.mark.audio` : Tests nécessitant l'accès audio
- `@pytest.mark.gui` : Tests nécessitant l'interface graphique

## Mocking avec unittest.mock

Les tests utilisent `unittest.mock` pour mocker les dépendances externes :

### Exemple : Mocking d'Ollama API

```python
from unittest.mock import patch, Mock

@patch('answer_generator.requests')
def test_generate_answer(mock_requests):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Answer"}
    mock_requests.post.return_value = mock_response
    
    generator = AnswerGenerator()
    answer = generator.generate_answer("Question?")
    assert answer == "Answer"
```

### Exemple : Mocking de Whisper

```python
@patch('transcription.WhisperModel')
def test_transcription(mock_whisper):
    mock_model = MagicMock()
    mock_whisper.return_value = mock_model
    # ... configuration du mock ...
```

## Exécution des Tests dans CI/CD

Pour l'intégration continue, utilisez :

```bash
pytest --tb=short --cov=. --cov-report=xml
```

## Dépannage des Tests

### Tests échouent avec "ModuleNotFoundError"

```bash
# S'assurer d'être dans le répertoire du projet
cd /Users/w999/Desktop/text-to-speech
pytest
```

### Tests audio échouent

Les tests audio sont mockés, mais si vous avez des problèmes :

```bash
# Exclure les tests audio
pytest -m "not audio"
```

### Tests lents timeout

```bash
# Exclure les tests lents
pytest -m "not slow"
```

## Exemples de Sortie

### Exécution réussie

```
============================= test session starts ==============================
platform darwin -- Python 3.13.9, pytest-7.4.0
collected 25 items

tests/test_question_detector.py::TestQuestionDetector::test_detects_question_mark PASSED
tests/test_answer_generator.py::TestAnswerGenerator::test_check_ollama_running_success PASSED
...

============================== 25 passed in 2.34s ===============================
```

### Avec couverture

```
----------- coverage: platform darwin, python 3.13.9 -----------
Name                      Stmts   Miss  Cover   Missing
---------------------------------------------------------
answer_generator.py          45      5    89%   32-36
question_detector.py         50      2    96%   88-89
...
---------------------------------------------------------
TOTAL                       200     15    93%
```

