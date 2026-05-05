Mission - Développez un agent IA pour l'apprentissage des échecs
Mission

Comment allez-vous procéder ?
Barre

 

Cette mission suit un scénario de projet professionnel.
Vous pouvez suivre les étapes pour vous aider à réaliser vos livrables.

 

Avant de démarrer, nous vous conseillons de :

 

lire toute la mission et ses documents liés ;

prendre des notes sur ce que vous avez compris ;

consulter les étapes pour vous guider ; 

préparer une liste de questions pour votre session de mentorat.

 

Prêt à mener la mission ? 
Barre

 

Vous êtes missionné en tant qu’IA Engineer junior pour le compte de la Fédération Française des Échecs (FFE).

                                                      logo de la fédération française des échecs

 

 

La FFE est l’organisation officielle chargée de promouvoir et développer le jeu d’échecs en France. En vue des futurs championnats d’Europe jeune, elle souhaite proposer un agent intelligent capable d’accompagner les jeunes espoirs dans l’apprentissage des ouvertures aux échecs.

 

Vous êtes chargé de développer un POC (Proof of Concept) de cet agent en 2 semaines.

 

Vous recevez un mail d’Alan, votre responsable technique, vous confiant la mission : 

 

 

 

De : Alan

À : moi

Objet : Mission POC – Agent IA ouvertures échecs (FFE)

Bonjour,

 

Comme convenu, je reviens vers toi pour te donner le contexte et les attendus de la mission confiée par la Fédération Française des Échecs (FFE).

 

La FFE souhaite, en vue des championnats d’Europe, disposer d’un agent intelligent permettant aux jeunes espoirs de s’entraîner sur les ouvertures.

L’agent IA devra guider les jeunes espoirs en :

leur proposant les meilleurs coups issus de la théorie, 

le contexte des ouvertures via des données enrichies par les parties historiques, 

des vidéos explicatives pertinentes, 

et une évaluation de la position par un moteur spécialisé (exemple Stockfish) si la partie s’écarte des sentiers battus.

 

Notre rôle est de réaliser un Proof of Concept (POC) qui démontre la faisabilité et la valeur ajoutée d’un tel agent.

 

Une compétition Kaggle s’est tenue récemment sur l’affrontement des LLM leaders (gemini, grok, gpt,...) aux échecs. Les LLM n'étaient pas dotés d'outils externes tels que des moteurs d'analyse ou de fonctions d'évaluation et ne se sont affrontés qu'avec leurs connaissances internes.

Regarde comment la compréhension de la position et du jeu d’échecs est transmise aux LLM (échiquier, derniers mouvements, coups possibles...), cela peut être instructif pour l’intégration de notre agent aux échecs.

Pour le POC, tu peux partir sur le modèle de ton choix.

 

Objectif de la mission : développer, en 2 semaines, une première version fonctionnelle qui :

Propose une interface Angular avec échiquier interactif (ngx-chessboard) : 

https://github.com/OpenClassrooms-Student-Center/material-chessboard

Guide l’utilisateur grâce à un agent IA connecté à :

une identification de la position en cours par identifiant fen.

un Stockfish (moteur d’échecs spécialisé),

des APIs Lichess (bibliothèque d’ouvertures et parties de références)

une intégration des données issues de Wikichess dans une base Milvus  pour la recherche vectorielle (toutes sources pertinentes sont acceptées)

un affichage de vidéos explicatives YouTube pertinentes (relatives à la position en cours) grâce à youtube api. 


Livrables attendus :

Système développé avec Lang Graph, Fastapi, Milvus et Mongodb.

Code accessible via un dépôt Git

Démonstration de l’Agent IA au client (exécution locale avec docker compose).

 

Merci pour ton investissement et ton travail.

À bientôt !

 

Alan

À ce stade de votre mission, vous décidez donc de concevoir un système qui :

stocke les vidéos pertinentes,
analyse chaque vidéo pour en extraire les frames,
sur chaque Frame, détecte la présence d'un échiquier et convertit la position en notation FEN.
Prévoyez la démonstration de votre POC.

 

Quelques heures plus tard

Barre

 

Vous recevez un message sur Slack de votre responsable Alan : 

 

Ah oui, j’oubliais une chose importante. Nous savons déjà que la simple requête textuelle pour obtenir la bonne vidéo YouTube est limitante. On risque de proposer une vidéo de 45 minutes sur la Sicilienne alors que l'utilisateur a juste besoin de l'explication du coup en cours. J'aimerais donc que tu profites de ce POC pour étudier une solution plus avancée. L'idée serait de concevoir un système qui : Stocke les vidéos pertinentes. Analyse chaque vidéo pour en extraire les frames (images). Sur chaque frame, détecte la présence d'un échiquier et convertit la position en notation FEN (Forsyth-Edwards Notation) grâce à un modèle de vision (type board-to-FEN). Cela nous permettrait de rechercher une position exacte dans notre catalogue de vidéos et de renvoyer le lien avec le timestamp précis. Ce système pourrait être porté par un serveur MCP (Model Context Protocol) pour s’interfacer facilement avec notre application. Livrables spécifiques pour cette étude (pas à développer, mais à concevoir) : Une note sur les bénéfices attendus et les limites de ce système. Un schéma d'architecture technique de la solution MCP. Une étude de faisabilité (coût estimé de mise en place et de fonctionnement). C'est une partie plus stratégique de ta mission, qui montrera au client notre vision à long terme. Merci, Alan

 

Pour cette dexième partie de mission, vous allez concevoir les livrables attendus (mais pas les développer) :
une note sur le bénéfice attendu les limites de ce système
un schéma d'architecture technique de la solution MCP
une étude de faisabilité avec estimation des coûts.
Cette étude permettra d’appuyer la démonstration de votre POC, tant dans ses limites que dans ses possibilités d’évolutions.

Cette mission est entièrement guidée.
Suivez les étapes ci-dessous et consultez la fiche d’autoévaluation de la dernière étape.

 

Étapes
La première étape consiste à préparer votre poste de travail. Vous allez mettre en place la structure du projet, initialiser le dépôt Git, et créer le fichier docker-compose.yml de base qui orchestrera les différents services (FastAPI, Milvus, MongoDB, Angular).

 

Prérequis :

Avoir lu et compris l'intégralité de la note de mission.

Avoir installé Git, Docker et Docker Compose sur votre poste.

Résultats attendus :

Un dépôt Git créé avec unREADME.mdinitial.

Une structure de dossiers claire (ex:backend/,frontend/).

Un fichierdocker-compose.ymlqui lance un service "Hello World" FastAPI.

Recommandations :

Commencez par le backend. Créez une route simple/api/v1/healthchecksur FastAPI pour vérifier que le conteneur Docker fonctionne correctement.

Utilisez des variables d'environnement pour la configuration (ports, etc.) dès le début.

Points de vigilance :

Vérifier que les versions des services (Python, Node.js) sont bien définies dans vos Dockerfiles pour assurer la reproductibilité.

S'assurer que les ports des conteneurs ne rentrent pas en conflit avec d'autres services sur votre machine.

Outils :

Visual Studio Code avec l'extension Docker.

Git.

Docker Desktop.

Ressources :

Documentation de FastAPI.

Tutoriel sur Docker avec FastAPI.

Vous allez maintenant implémenter la logique principale de l'agent. Il s'agit de créer les endpoints FastAPI qui, pour une position donnée (au format FEN), interrogeront l'API de Lichess pour trouver les coups théoriques et, si aucun n'est trouvé, feront appel à Stockfish pour évaluer la position.

Rappels, aux Échecs : 

Une ouverture aux échecs est le début de la partie, c’est-à-dire les premiers coups joués.
Un coup théorique = déjà reconnu par la théorie. Il est donc sûr, étudié, validé.
Un coup non théorique = sort des sentiers battus. Il est donc parfois créatif, parfois mauvais, parfois une découverte !
Une position désigne la situation des pièces sur l’échiquier à un moment donné de la partie.
 

Prérequis :

Avoir un environnement backend fonctionnel.

Résultats attendus :

Un endpoint /api/v1/moves/{fen} qui retourne les coups théoriques possibles depuis Lichess.

Un endpoint /api/v1/evaluate/{fen} qui retourne l'évaluation de Stockfish (par exemple, en centipawns).

Recommandations :

Utilisez la bibliothèque Python chess pour valider les positions FEN et la légalité des coups.

Créez une classe ou un module "service" pour encapsuler la logique d'appel à Lichess et à Stockfish, afin de garder votre code API propre.

Points de vigilance :

Gérer les erreurs et les timeouts lors des appels aux APIs externes (Lichess).

Faire attention aux limites de requêtes de l'API Lichess.

Outils :

Bibliothèque python-chess.

Bibliothèque Stockfish pour Python.

Postman ou l'interface Swagger de FastAPI pour tester vos endpoints.

Ressources :

Documentation de l'API Lichess.

Vous allez enrichir l'agent avec du contexte. L'objectif est de mettre en place un système de Retrieval-Augmented Generation (RAG) simple. 

Préparez un petit jeu de données textuelles depuis Wikichess, transformez le en vecteurs (embeddings) et indexez-le dans Milvus. Enfin, vous créerez un endpoint pour rechercher des informations sur une ouverture donnée.

Prérequis :

Avoir le conteneur Milvus qui tourne via Docker Compose.

Résultats attendus :

Un script pour traiter et charger les données dans Milvus.

Un endpoint /vector-search qui retourne des informations textuelles pertinentes sur l'ouverture demandée via une recherche vectorielle.

Recommandations :

Commencez avec 5 ou 10 articles de Wikichess sur les ouvertures les plus populaires (Italienne, Espagnole, Sicilienne...).

Utilisez un modèle d'embedding léger de la bibliothèque sentence-transformers (ex: qwen3B-embedding-0.6B).

LangGraph peut être utilisé ici pour orchestrer l'appel à Milvus et formater la réponse.

Points de vigilance :

Bien configurer la connexion entre votre API FastAPI et le service Milvus dans le réseau Docker.

La qualité de la recherche dépendra de la qualité des données et du chunking (découpage du texte) que vous ferez.

Outils suggérés :

Milvus.

Bibliothèque sentence-transformers.

Bibliothèque pymilvus.

Ressources :

Cours sur LangChain & Vector Databases.

Vous allez maintenant ajouter la fonctionnalité de recherche de vidéos explicatives. L'objectif est de créer un endpoint qui, pour une ouverture donnée, recherche des vidéos YouTube pertinentes et les retourne avec leurs métadonnées.

 

Prérequis :

Avoir une clé API YouTube valide

Résultat attendu :

Un endpoint/api/v1/videos/{opening}qui retourne des vidéos YouTube pertinentes.

Intégration dans le workflow LangGraph pour proposer automatiquement des ressources vidéo.

Recommandations : 

Utilisez la bibliothèquegoogle-api-python-clientpour interagir avec l'API YouTube. 

Créez des requêtes de recherche intelligentes en combinant le nom de l'ouverture avec des mots-clés comme "chess opening", "tutorial", "explanation".

Points de vigilance :

Gérer les quotas de l'API YouTube.

Filtrer les résultats pour ne garder que les vidéos de qualité et pertinentes.

Il faut que les liens des vidéos soient affichés, si le streaming est possible c’est encore mieux. 

Gérer les cas où aucune vidéo n'est trouvée. 

Outils :

Google API Python Client

API YouTube Data v3

Ressources :

Documentation API YouTube

Vous allez créer l'interface utilisateur qui permettra aux utilisateurs d'interagir avec l'agent. L'interface comprendra un échiquier interactif et un panneau de recommandations de l'agent.

 

Prérequis :

Avoir installé Node.js et Angular CLI.

Résultats attendus :

Une application Angular avec un échiquier fonctionnel (ngx-chessboard).

Un panneau affichant les recommandations de l'agent (coups suggérés, contexte, vidéos).

Communication avec l'API backend via des services Angular.

Recommandations : 

Utilisez la librairie ngx-chessboard pour l'échiquier interactif. 

Créez des services Angular pour communiquer avec votre API backend. 

Implémentez une interface utilisateur claire et intuitive.

Points de vigilance :

Gérer les états de chargement et les erreurs réseau.

Synchroniser correctement l'état de l'échiquier avec l'agent IA.

Optimiser les appels API pour éviter les requêtes inutiles.

Outils :

Angular CLI

ngx-chessboard

Angular HttpClient

Ressources :

Documentation Angular

Documentation ngx-chessboard

Le cours Perfectionnez-vous sur Angular.

Vous allez finaliser la containerisation complète de votre application et préparer la démonstration client.

 

Prérequis :

Avoir tous les services fonctionnels.

Résultats attendus :

Un docker-compose.yml complet orchestrant tous les services.

Une documentation d'installation et de démarrage.

Une application prête pour la démonstration.

Recommandations : 

Testez l'ensemble du système en partant d'une installation fraîche. 

Créez un README détaillé avec les instructions de démarrage. 

Préparez quelques positions d'échecs intéressantes pour la démonstration.

Points de vigilance :

Vérifier que tous les services démarrent.

S'assurer que les volumes Docker persistants sont bien configurés. Par exemple : 

Vérifier la déclaration du volume 

Contrôler avecdocker volume lsetdocker volume inspect.

Tester en recréant les conteneurs pour s’assurer que les données persistent.

Tester votre application de bout en bout afin de vous assurer que tous les services soient correctement interfacés.

Vous allez concevoir et documenter le système avancé d'analyse vidéo demandé par votre responsable, sans l'implémenter.

 

Prérequis :

Avoir compris les enjeux du système d'analyse vidéo.

Résultats attendus :

Une note détaillée de 8-10 pages sur les bénéfices et limites du système incluant

Un schéma d'architecture technique utilisant MCP.

Une étude de faisabilité avec estimations de coûts (coûts du build + opex).

Recommandations : 

Recherchez les technologies existantes pour la détection d'échiquiers (OpenCV, modèles de vision). 

Évaluez les coûts de stockage, de traitement et d'API. 

Proposez une architecture modulaire et évolutive.

Points de vigilance :

Être réaliste dans les estimations de coûts et de complexité.

Identifier les risques techniques et business.

Proposer une ou deux  alternatives et des étapes de développement.

Ressources :

Documentation Model Context Protocol avec FastMCP

Articles sur la détection d'échiquiers par vision computationnelle

Pour vérifier que vous n'avez rien oublié dans la réalisation de votre mission, téléchargez et complétez la fiche d'autoévaluation.

Parlez-en avec votre mentor durant votre dernière session de mentorat.