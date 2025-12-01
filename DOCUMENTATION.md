# Documentation du Projet de Transcription Audio en Temps Réel avec Intelligence Artificielle

## Introduction

Ce projet consiste en une application de transcription audio en temps réel qui utilise des modèles d'intelligence artificielle locaux pour générer des réponses aux questions détectées dans le texte transcrit. L'application capture l'audio système provenant de n'importe quelle application comme Teams, Zoom ou Discord, le convertit en texte grâce au modèle Whisper, détecte automatiquement les questions posées et génère des réponses pertinentes en utilisant Ollama qui est un système de modèles de langage locaux.

L'objectif principal de cette application est de fournir un assistant intelligent qui fonctionne entièrement en local, garantissant ainsi la confidentialité des données puisque tout le traitement se fait sur la machine de l'utilisateur sans envoyer d'informations vers des serveurs externes.

## Architecture Générale

L'application est structurée en plusieurs modules Python qui communiquent entre eux pour réaliser le traitement complet du flux audio jusqu'à la génération de réponses. Le point d'entrée principal est le fichier main.py qui contient l'interface graphique et orchestre tous les composants. Les autres modules sont audio_capture.py pour la capture audio, transcription.py pour la conversion parole-texte, question_detector.py pour identifier les questions et answer_generator.py pour générer les réponses via Ollama.

Le flux de données suit un chemin logique : l'audio système est capturé par AudioCapture, puis transmis à TranscriptionEngine qui le convertit en texte, ensuite QuestionDetector analyse ce texte pour trouver les questions, et enfin AnswerGenerator utilise le contexte de la conversation pour produire des réponses appropriées. Tout cela est présenté à l'utilisateur dans une interface graphique moderne développée avec CustomTkinter.

## Composants Principaux

### Module main.py et classe TranscriptionApp

La classe TranscriptionApp hérite de ctk.CTk qui est la classe de base de CustomTkinter pour créer des fenêtres graphiques. Cette classe gère toute l'interface utilisateur et coordonne les différents composants de l'application. Lors de l'initialisation, elle charge la configuration depuis le fichier config.json, crée les différents onglets de l'interface, configure la barre système si possible, et prépare les raccourcis clavier.

La méthode start_recording initialise les composants nécessaires comme le moteur de transcription et le détecteur de questions, puis démarre la capture audio. Quand un chunk audio arrive, la méthode on_audio_chunk est appelée en callback. Cette méthode vérifie d'abord que l'audio n'est pas trop silencieux, puis lance la transcription dans un thread séparé pour ne pas bloquer l'interface. Le texte transcrit est ensuite accumulé jusqu'à avoir une phrase complète, puis ajouté à une queue de messages qui sera traitée par process_messages dans le thread principal pour mettre à jour l'interface.

La gestion de la configuration se fait via load_config qui cherche d'abord un fichier config.json dans le répertoire courant, puis utilise des valeurs par défaut si le fichier n'existe pas. La méthode save_config permet de sauvegarder les modifications de configuration.

### Module audio_capture.py et classe AudioCapture

La classe AudioCapture est responsable de la capture de l'audio système en utilisant la bibliothèque sounddevice. Elle détecte automatiquement les devices audio de type loopback qui permettent de capturer l'audio qui sort des haut-parleurs plutôt que celui qui entre par le microphone.

La méthode _find_loopback_device parcourt tous les devices audio disponibles et cherche ceux qui correspondent aux noms de drivers virtuels comme BlackHole sur macOS ou VB-Audio sur Windows. Sur macOS, elle cherche spécifiquement dans les devices Core Audio ceux qui contiennent les mots-clés blackhole, vb-cable ou loopback dans leur nom. Sur Windows, elle cherche dans les devices WASAPI ceux qui contiennent des mots comme loopback, stereo mix ou vb-audio.

Une fois le device trouvé, la méthode _get_device_sample_rate teste différents taux d'échantillonnage pour trouver celui que le device supporte nativement, ce qui évite d'avoir à faire du resampling qui consomme des ressources. Le taux cible est 16000 Hz qui est optimal pour Whisper, mais si le device ne le supporte pas, on utilise son taux par défaut et on fait du resampling plus tard si nécessaire.

La capture audio se fait via un InputStream de sounddevice qui appelle la méthode _audio_callback à chaque fois qu'un chunk audio est disponible. Ces chunks sont ajoutés à une queue, puis un thread séparé les traite dans _process_audio_chunks. Ce thread accumule les chunks jusqu'à détecter une période de silence suffisamment longue, ce qui indique probablement la fin d'une phrase, puis appelle le callback avec le buffer complet.

### Module transcription.py et classe TranscriptionEngine

La classe TranscriptionEngine encapsule l'utilisation du modèle Whisper via la bibliothèque faster-whisper. Le modèle est chargé de manière paresseuse lors du premier appel à transcribe_chunk, ce qui évite de charger un modèle lourd si l'utilisateur ne démarre jamais l'enregistrement.

La méthode transcribe_chunk prend un tableau numpy d'audio en float32 à 16000 Hz et retourne le texte transcrit. Elle utilise la méthode transcribe de Whisper avec des paramètres de VAD, Voice Activity Detection, qui permettent de mieux détecter les phrases complètes. Les paramètres incluent min_silence_duration_ms à 1200 millisecondes pour attendre la fin d'une phrase, un seuil de VAD à 0.5, et une durée minimale de parole de 250 millisecondes.

Le texte transcrit est nettoyé pour enlever les espaces multiples et les phrases de prompt qui pourraient être accidentellement transcrites. Chaque transcription réussie est ajoutée à un buffer de conversation qui garde les dernières transcriptions pour fournir du contexte aux réponses générées.

### Module question_detector.py et classe QuestionDetector

La classe QuestionDetector utilise des patterns regex et une analyse de mots-clés pour identifier les questions dans le texte. Elle maintient une liste de mots interrogatifs comme who, what, where, when, why, how, ainsi que des verbes auxiliaires qui peuvent commencer une question comme is, are, can, would.

La méthode is_question calcule un score de confiance basé sur plusieurs indicateurs. La présence d'un point d'interrogation ajoute 0.5 au score, un mot interrogatif au début ajoute 0.3, la correspondance avec un pattern regex ajoute 0.2, et une structure de question avec inversion du sujet ajoute encore 0.2. Le score est ensuite normalisé entre 0 et 1, et comparé à un seuil qui dépend de la sensibilité configurée.

La sensibilité fonctionne de manière inversée : une sensibilité élevée signifie un seuil plus bas, donc plus de détections. Le seuil est calculé comme 0.3 plus 0.4 multiplié par un moins la sensibilité, ce qui donne un seuil de 0.3 pour sensibilité 1.0 et 0.7 pour sensibilité 0.0.

### Module answer_generator.py et classe AnswerGenerator

La classe AnswerGenerator communique avec l'API Ollama via des requêtes HTTP. Ollama est un serveur local qui expose une API REST pour utiliser des modèles de langage. L'URL par défaut est http://localhost:11434 et l'endpoint pour générer des réponses est /api/chat.

La méthode check_ollama_running fait une requête GET vers /api/tags pour vérifier si le serveur répond. Si la requête réussit avec un code 200, Ollama est considéré comme actif. La méthode check_model_available fait la même requête mais vérifie ensuite dans la liste des modèles retournés si le modèle configuré est présent.

La méthode generate_answer construit un prompt qui inclut le contexte de conversation si disponible, puis envoie une requête POST vers l'API chat d'Ollama. Le prompt est structuré pour demander une réponse concise et directe. La réponse de l'API contient le texte généré dans le champ message.content, qui est extrait et retourné.

## Installation et Configuration

Pour installer l'application, il faut d'abord s'assurer que Python 3.8 ou supérieur est installé. Ensuite, il faut installer Ollama qui est le serveur de modèles de langage. Sur macOS, on peut utiliser Homebrew avec la commande brew install ollama. Sur Linux, on utilise le script d'installation fourni par Ollama. Sur Windows, il faut télécharger l'installateur depuis le site web d'Ollama.

Une fois Ollama installé, il faut télécharger au moins un modèle de langage avec la commande ollama pull llama3.2:3b. Ce modèle fait environ 2 gigaoctets et sera téléchargé la première fois qu'on l'utilise. D'autres modèles sont disponibles comme llama3.2:1b qui est plus petit et plus rapide, ou mistral qui est une alternative.

Les dépendances Python s'installent avec pip install -r requirements.txt. Cette commande installe toutes les bibliothèques nécessaires comme faster-whisper pour la transcription, customtkinter pour l'interface, sounddevice pour l'audio, et les autres dépendances.

Pour la configuration audio, sur macOS il faut installer BlackHole ou VB-Cable qui sont des drivers audio virtuels permettant de capturer l'audio système. Après installation, il faut redémarrer l'ordinateur. Ensuite, dans les Réglages Système, il faut créer un Multi-Output Device qui combine les haut-parleurs et le driver virtuel, et sélectionner ce device comme sortie audio. Ainsi, l'audio va à la fois vers les haut-parleurs pour qu'on puisse l'entendre et vers le driver virtuel pour que l'application puisse le capturer.

Le fichier config.json contient tous les paramètres de l'application. Si ce fichier n'existe pas, l'application utilise des valeurs par défaut. Les paramètres importants incluent whisper_model qui détermine la taille du modèle Whisper, ollama_model qui spécifie quel modèle Ollama utiliser, auto_answer qui active ou désactive les réponses automatiques, et detection_sensitivity qui contrôle la sensibilité de détection des questions.

## Utilisation de l'Application

Pour lancer l'application, on exécute simplement python3 main.py dans le terminal. L'interface graphique s'ouvre avec plusieurs onglets. L'onglet Transcription affiche le texte transcrit en temps réel au fur et à mesure que l'audio est capturé. L'onglet Questions liste toutes les questions qui ont été détectées automatiquement. L'onglet Answers montre les réponses générées par l'IA.

Le bouton Start Recording démarre la capture audio. Quand on clique dessus, l'application initialise le moteur de transcription si ce n'est pas déjà fait, crée une instance d'AudioCapture qui trouve automatiquement le bon device audio, et commence à capturer les chunks audio. Chaque chunk est transcrit et le texte apparaît dans l'interface.

Si une question est détectée et que auto_answer est activé, l'application génère automatiquement une réponse. Sinon, on peut sélectionner du texte dans l'onglet Transcription et cliquer sur Answer Selected pour obtenir une réponse manuellement. Le bouton Copy Last Answer permet de copier la dernière réponse générée dans le presse-papiers.

Le bouton Settings ouvre une fenêtre de configuration où on peut changer le modèle Whisper, le modèle Ollama, la sensibilité de détection, et d'autres paramètres. Les modifications sont sauvegardées automatiquement dans config.json.

## Dépannage et Problèmes Courants

Si l'application affiche Ollama is not running, cela signifie que le serveur Ollama n'est pas démarré. On peut vérifier avec la commande ollama list qui devrait retourner la liste des modèles disponibles. Si cette commande échoue, il faut démarrer Ollama manuellement ou redémarrer l'ordinateur car Ollama devrait démarrer automatiquement au boot.

Le message No loopback audio device found indique qu'aucun device virtuel n'a été trouvé. Sur macOS, il faut installer BlackHole ou VB-Cable et redémarrer. Sur Windows, il faut activer Stereo Mix dans les paramètres audio ou installer VB-Audio Virtual Cable. L'application fournit des messages d'aide détaillés dans ce cas.

Si les niveaux audio sont à 0.0000, cela signifie que l'audio n'est pas routé vers le device virtuel. Il faut vérifier que le Multi-Output Device est bien sélectionné comme sortie audio dans les Réglages Système. On peut tester avec le script setup_vb_cable.py qui vérifie si le device reçoit bien de l'audio.

Quand la transcription est vide, plusieurs causes sont possibles. L'audio peut être trop silencieux et être filtré par le seuil de silence. Il faut augmenter le volume système. Le modèle Whisper peut être trop petit et ne pas bien transcrire. On peut essayer le modèle small au lieu de base. Le VAD peut filtrer tout l'audio si les paramètres sont trop stricts.

Pour les questions non détectées, il faut augmenter la sensibilité dans les paramètres. Il faut aussi s'assurer que les questions ont bien un point d'interrogation ou commencent par un mot interrogatif. Parler plus clairement peut aussi aider.

L'application fournit plusieurs outils de diagnostic. Le script list_audio_devices.py liste tous les devices audio disponibles avec leur type. Le script diagnose_audio.py fait un diagnostic complet de la configuration audio et donne des recommandations spécifiques à la plateforme. Le script test_audio_capture.py teste si la capture audio fonctionne et affiche les niveaux audio en temps réel.

## Tests

Les tests sont organisés dans le répertoire tests et utilisent pytest comme framework de test. Chaque module a son propre fichier de test qui contient des tests unitaires pour toutes les méthodes importantes. Les tests utilisent unittest.mock pour mocker les dépendances externes comme les appels API à Ollama ou l'utilisation de Whisper, ce qui permet de tester la logique sans avoir besoin des vrais services.

Les tests pour QuestionDetector vérifient que la détection de questions fonctionne correctement avec différents types de phrases, que la sensibilité fonctionne comme prévu, et que les cas limites comme les chaînes vides sont gérés. Les tests pour AnswerGenerator mockent les requêtes HTTP pour simuler les réponses d'Ollama et tester les différents cas comme le succès, les erreurs de connexion, et les modèles non disponibles.

Les tests pour TranscriptionEngine mockent le modèle Whisper pour éviter de charger un vrai modèle qui serait très lent. Ils vérifient que l'initialisation fonctionne, que la transcription retourne le bon texte, et que les cas d'erreur sont gérés. Les tests pour AudioCapture mockent sounddevice pour simuler différents devices audio et tester la détection automatique et la capture.

Pour exécuter les tests, on utilise simplement la commande pytest dans le répertoire du projet. On peut exécuter tous les tests avec pytest, ou un fichier spécifique avec pytest tests/test_question_detector.py, ou même un test spécifique avec pytest tests/test_question_detector.py::TestQuestionDetector::test_detects_question_mark. L'option -v donne plus de détails sur les tests exécutés.

## Conclusion

Cette application démontre l'intégration de plusieurs technologies d'intelligence artificielle pour créer un assistant vocal intelligent qui fonctionne entièrement en local. L'utilisation de Whisper pour la transcription, de patterns de détection pour identifier les questions, et d'Ollama pour générer des réponses contextuelles, montre comment on peut combiner différents composants pour créer une solution complète. Le fait que tout fonctionne localement garantit la confidentialité des données, ce qui est important pour les utilisateurs qui traitent des informations sensibles.
