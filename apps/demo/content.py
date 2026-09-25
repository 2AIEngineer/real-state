"""Realistic words for the demo: people, places, and what residents write."""

FIRST_NAMES_FEMALE = [
    "Salma",
    "Yasmine",
    "Imane",
    "Khadija",
    "Fatima Zahra",
    "Meryem",
    "Nadia",
    "Sanaa",
    "Hind",
    "Leila",
    "Ghita",
    "Asmae",
    "Soukaina",
    "Kenza",
    "Rim",
    "Houda",
    "Zineb",
    "Loubna",
    "Samira",
    "Claire",
    "Sophie",
    "Camille",
    "Julie",
    "Aurélie",
    "Nathalie",
    "Emma",
    "Chloé",
    "Inès",
    "Sarah",
    "Amina",
    "Hajar",
    "Oumaima",
    "Wiam",
    "Najat",
    "Latifa",
    "Btissam",
    "Siham",
    "Malika",
    "Rachida",
]
FIRST_NAMES_MALE = [
    "Youssef",
    "Mehdi",
    "Omar",
    "Karim",
    "Anas",
    "Hamza",
    "Amine",
    "Othmane",
    "Reda",
    "Ayoub",
    "Adil",
    "Hicham",
    "Rachid",
    "Said",
    "Mustapha",
    "Driss",
    "Abdelilah",
    "Nabil",
    "Tarik",
    "Ilyas",
    "Thomas",
    "Nicolas",
    "Julien",
    "Pierre",
    "Antoine",
    "Lucas",
    "Hugo",
    "Maxime",
    "Paul",
    "Louis",
    "Soufiane",
    "Zakaria",
    "Ismail",
    "Walid",
    "Khalid",
    "Jamal",
    "Aziz",
    "Hassan",
    "Brahim",
    "Fouad",
]
LAST_NAMES = [
    "Benali",
    "El Amrani",
    "Alaoui",
    "Bennani",
    "Tazi",
    "Idrissi",
    "Berrada",
    "Chraibi",
    "Fassi",
    "Lahlou",
    "Sqalli",
    "Kettani",
    "Benjelloun",
    "Ouazzani",
    "Mernissi",
    "Ziani",
    "Haddad",
    "El Mansouri",
    "Belkadi",
    "Naciri",
    "Rami",
    "Tahiri",
    "Zouhair",
    "Amrani",
    "Cherkaoui",
    "Bouzidi",
    "Hajji",
    "Kabbaj",
    "Lamrani",
    "Moussaoui",
    "Ouali",
    "Sabri",
    "Filali",
    "Guessous",
    "Martin",
    "Bernard",
    "Dubois",
    "Durand",
    "Lefebvre",
    "Moreau",
    "Laurent",
    "Garnier",
    "Rousseau",
]

SYNDICATS = [
    {
        "name": "Syndic Atlantique",
        "legal_name": "Atlantique Gestion Immobilière SARL",
        "registration_number": "RC 412587",
        "contact_email": "contact@atlantique-syndic.test",
        "contact_phone": "+212 522 36 48 10",
        "address": "27, boulevard d'Anfa, 7e étage",
        "city": "Casablanca",
        "country": "Maroc",
        "properties": [
            {
                "name": "Résidence Les Jardins d'Anfa",
                "description": "Deux tours résidentielles avec piscine et jardin paysager, "
                "à dix minutes de la corniche.",
                "address": "Boulevard Abdelkrim Al Khattabi, Anfa",
                "city": "Casablanca",
                "buildings": ["Tour Jasmin", "Tour Oranger"],
            },
            {
                "name": "Résidence Marina Bay",
                "description": "Résidence de standing face à la marina, commerces au rez-de-chaussée.",
                "address": "Boulevard des Almohades, Casablanca Marina",
                "city": "Casablanca",
                "buildings": ["Bâtiment Corail", "Bâtiment Nacre"],
            },
        ],
    },
    {
        "name": "Syndic Atlas Habitat",
        "legal_name": "Atlas Habitat Services SA",
        "registration_number": "RC 98314",
        "contact_email": "bonjour@atlas-habitat.test",
        "contact_phone": "+212 524 43 17 02",
        "address": "15, avenue Mohammed V, Guéliz",
        "city": "Marrakech",
        "country": "Maroc",
        "properties": [
            {
                "name": "Domaine Palmeraie",
                "description": "Résidence fermée au cœur de la Palmeraie : villas-appartements, "
                "spa et terrains de sport.",
                "address": "Circuit de la Palmeraie, km 6",
                "city": "Marrakech",
                "buildings": ["Riad Nord", "Riad Sud"],
            },
            {
                "name": "Résidence Hivernage Park",
                "description": "Appartements familiaux dans le quartier de l'Hivernage, "
                "proches des écoles et des commerces.",
                "address": "Avenue Echouhada, Hivernage",
                "city": "Marrakech",
                "buildings": ["Bloc Atlas", "Bloc Ourika"],
            },
        ],
    },
]

PROMOTERS = [
    {
        "name": "Addoha Promotion",
        "legal_name": "Groupe Addoha Promotion SA",
        "registration_number": "RC 55120",
        "contact_email": "commercial@addoha-promo.test",
        "contact_phone": "+212 522 99 12 12",
        "address": "Km 7, route de Rabat, Aïn Sebaâ, Casablanca",
    },
    {
        "name": "Palmeraie Développement",
        "legal_name": "Palmeraie Développement SA",
        "registration_number": "RC 77301",
        "contact_email": "ventes@palmeraie-dev.test",
        "contact_phone": "+212 524 30 80 80",
        "address": "Palmeraie Business Center, Marrakech",
    },
]

ANNOUNCEMENTS = [
    (
        "meeting",
        "important",
        "Assemblée générale annuelle",
        "L'assemblée générale ordinaire se tiendra dans la salle polyvalente. Ordre du jour : "
        "approbation des comptes, budget prévisionnel, travaux de ravalement. Votre présence ou "
        "votre pouvoir est indispensable pour atteindre le quorum.",
    ),
    (
        "maintenance",
        "important",
        "Coupure d'eau programmée",
        "Une coupure d'eau aura lieu de 9h à 13h pour le remplacement de la colonne montante. "
        "Pensez à faire des réserves.",
    ),
    (
        "maintenance",
        "normal",
        "Entretien des ascenseurs",
        "Le prestataire procédera à la maintenance annuelle des ascenseurs. Un seul ascenseur "
        "sera en service pendant l'intervention.",
    ),
    (
        "security",
        "urgent",
        "Rappel sécurité : badges d'accès",
        "Suite à plusieurs intrusions signalées dans le quartier, merci de ne jamais prêter votre "
        "badge et de refermer systématiquement la porte du parking.",
    ),
    (
        "general",
        "normal",
        "Nouveaux horaires du gardiennage",
        "Le poste de garde est désormais ouvert 24h/24. Le numéro d'urgence reste inchangé.",
    ),
    (
        "community",
        "normal",
        "Tri sélectif",
        "Des bacs de tri ont été installés au local poubelles. Papier et carton dans le bac bleu, "
        "plastique dans le bac jaune, verre dans le conteneur vert.",
    ),
    (
        "maintenance",
        "normal",
        "Désinsectisation des parties communes",
        "Une désinsectisation préventive des caves, gaines et parkings est programmée. Merci de "
        "laisser l'accès aux locaux techniques.",
    ),
    (
        "general",
        "normal",
        "Fermeture de la piscine pour hivernage",
        "La piscine ferme pour la saison hivernale. Réouverture prévue au printemps après "
        "vérification des installations.",
    ),
    (
        "meeting",
        "normal",
        "Réunion du conseil syndical",
        "Le conseil syndical se réunit pour préparer l'appel d'offres sur le nettoyage. Vos "
        "suggestions sont les bienvenues via la boîte à idées.",
    ),
    (
        "security",
        "important",
        "Exercice d'évacuation incendie",
        "Un exercice d'évacuation aura lieu en matinée. L'alarme retentira environ deux minutes ; "
        "rejoignez le point de rassemblement devant l'entrée principale.",
    ),
]

EVENTS = [
    (
        "Fête des voisins",
        "Apéritif convivial au jardin, chacun apporte un plat à partager.",
        "Jardin central",
    ),
    (
        "Atelier jardinage pour enfants",
        "Plantation de fleurs et d'herbes aromatiques avec les enfants.",
        "Potager partagé",
    ),
    (
        "Tournoi de tennis de la résidence",
        "Tournoi amical en double, inscriptions à la loge.",
        "Court de tennis",
    ),
    (
        "Soirée cinéma en plein air",
        "Projection d'un film familial au bord de la piscine.",
        "Terrasse de la piscine",
    ),
    (
        "Collecte solidaire de vêtements",
        "Déposez vos vêtements en bon état au profit d'une association locale.",
        "Hall d'entrée",
    ),
    (
        "Cours de yoga du samedi",
        "Séance ouverte à tous les niveaux, pensez à votre tapis.",
        "Salle polyvalente",
    ),
    ("Iftar partagé", "Rupture du jeûne conviviale entre résidents.", "Salle des fêtes"),
    (
        "Réunion d'information travaux",
        "Présentation du planning des travaux de façade par l'architecte.",
        "Salle polyvalente",
    ),
]

SURVEYS = [
    (
        "Horaires de la piscine",
        "Quels horaires d'ouverture préférez-vous pour la saison estivale ?",
        [
            ("Quel créneau d'ouverture préférez-vous ?", ["8h – 20h", "9h – 21h", "10h – 22h"]),
            ("Souhaitez-vous un créneau réservé aux nageurs ?", ["Oui", "Non", "Sans avis"]),
        ],
    ),
    (
        "Rénovation du hall d'entrée",
        "Aidez-nous à choisir l'ambiance du futur hall.",
        [
            (
                "Quelle ambiance préférez-vous ?",
                ["Moderne et épurée", "Traditionnelle marocaine", "Végétalisée"],
            ),
            (
                "Quel budget par lot vous semble raisonnable ?",
                ["Moins de 1 000 MAD", "1 000 à 2 500 MAD", "Plus de 2 500 MAD"],
            ),
        ],
    ),
    (
        "Satisfaction sur le nettoyage",
        "Votre avis sur la qualité du nettoyage des parties communes.",
        [
            (
                "Êtes-vous satisfait du nettoyage ?",
                ["Très satisfait", "Satisfait", "Peu satisfait", "Pas du tout"],
            ),
            ("Faut-il augmenter la fréquence du nettoyage des escaliers ?", ["Oui", "Non"]),
        ],
    ),
    (
        "Installation de bornes de recharge",
        "Projet d'équipement du parking en bornes pour véhicules électriques.",
        [
            (
                "Possédez-vous ou prévoyez-vous un véhicule électrique ?",
                ["Oui, déjà", "D'ici deux ans", "Non"],
            ),
            ("Seriez-vous prêt à participer au financement ?", ["Oui", "Non", "À discuter en AG"]),
        ],
    ),
]

LIBRARY_DOCUMENTS = [
    (
        "Rules and bylaws",
        "Règlement de copropriété",
        "Version consolidée du règlement de copropriété.",
    ),
    (
        "Rules and bylaws",
        "Règlement intérieur de la piscine",
        "Horaires, hygiène et sécurité à la piscine.",
    ),
    ("Meeting minutes", "Procès-verbal de l'AG 2025", "Compte rendu et résolutions votées."),
    (
        "Meeting minutes",
        "Procès-verbal du conseil syndical – mars",
        "Décisions sur le contrat de nettoyage.",
    ),
    (
        "Notices and communication",
        "Guide du nouveau résident",
        "Tout ce qu'il faut savoir en arrivant.",
    ),
    (
        "Notices and communication",
        "Planning des travaux de façade",
        "Calendrier prévisionnel bâtiment par bâtiment.",
    ),
    (
        "Forms",
        "Formulaire d'autorisation de travaux",
        "À remettre au syndic avant tout travaux privatifs.",
    ),
    ("Forms", "Demande de badge supplémentaire", "Formulaire de commande de badges d'accès."),
    (
        "Declarations",
        "Attestation d'assurance de l'immeuble",
        "Police multirisque de l'exercice en cours.",
    ),
    (
        "Service providers",
        "Contrat d'entretien des ascenseurs",
        "Conditions et contacts du prestataire.",
    ),
]

AMENITIES = [
    {
        "name": "Piscine",
        "description": "Bassin extérieur chauffé de 25 m avec pataugeoire.",
        "location": "Jardin central",
        "rules": "Douche obligatoire. Enfants de moins de 12 ans accompagnés.",
        "booking_mode": "SHARED",
        "capacity": 25,
        "requires_approval": False,
        "opening_time": "08:00",
        "closing_time": "20:00",
        "min_duration_minutes": 60,
        "max_duration_minutes": 180,
        "max_advance_days": 7,
    },
    {
        "name": "Salle de sport",
        "description": "Cardio, musculation guidée et poids libres.",
        "location": "Rez-de-chaussée",
        "rules": "Serviette obligatoire, rangez le matériel.",
        "booking_mode": "SHARED",
        "capacity": 8,
        "requires_approval": False,
        "opening_time": "06:00",
        "closing_time": "22:00",
        "min_duration_minutes": 30,
        "max_duration_minutes": 120,
        "max_advance_days": 7,
    },
    {
        "name": "Salle des fêtes",
        "description": "Salle de 80 m² avec cuisine équipée et terrasse.",
        "location": "Bâtiment principal, niveau -1",
        "rules": "Fin des festivités à 23h. État des lieux avant et après.",
        "booking_mode": "EXCLUSIVE",
        "capacity": 60,
        "requires_approval": True,
        "opening_time": "10:00",
        "closing_time": "23:00",
        "min_duration_minutes": 120,
        "max_duration_minutes": 600,
        "max_advance_days": 60,
        "fee": "500.00",
        "security_fee": "1500.00",
    },
    {
        "name": "Court de tennis",
        "description": "Court en résine éclairé.",
        "location": "Espace sportif",
        "rules": "Chaussures de tennis obligatoires.",
        "booking_mode": "EXCLUSIVE",
        "capacity": 4,
        "requires_approval": False,
        "opening_time": "07:00",
        "closing_time": "22:00",
        "min_duration_minutes": 60,
        "max_duration_minutes": 120,
        "max_advance_days": 14,
        "hourly_price": "80.00",
    },
]

PRODUCTS = [
    ("Bouteille d'eau minérale 5 L", "Boissons", "12.00"),
    ("Pack lait demi-écrémé 6 × 1 L", "Épicerie", "54.00"),
    ("Pain de campagne", "Boulangerie", "8.50"),
    ("Croissants (lot de 6)", "Boulangerie", "18.00"),
    ("Café en grains 1 kg", "Épicerie", "140.00"),
    ("Thé vert à la menthe 500 g", "Épicerie", "45.00"),
    ("Huile d'olive extra vierge 1 L", "Épicerie", "95.00"),
    ("Recharge gaz butane 12 kg", "Maison", "50.00"),
    ("Ampoules LED E27 (lot de 4)", "Maison", "79.00"),
    ("Sacs poubelle 50 L (rouleau)", "Maison", "22.00"),
    ("Lessive liquide 3 L", "Entretien", "89.00"),
    ("Produit vaisselle 1 L", "Entretien", "19.50"),
    ("Pile AA (lot de 8)", "Maison", "45.00"),
    ("Bouquet de fleurs de saison", "Services", "150.00"),
    ("Lavage de voiture au parking", "Services", "120.00"),
]

SERVICE_REQUESTS = {
    "plumbing": [
        ("Fuite sous l'évier", "L'eau goutte en continu sous l'évier de la cuisine."),
        ("Chasse d'eau qui coule", "La chasse d'eau ne s'arrête plus depuis hier soir."),
        ("Pression d'eau faible", "Très peu de pression à la douche le matin."),
    ],
    "electricity": [
        ("Prise hors service", "La prise du salon ne fonctionne plus."),
        ("Éclairage du palier en panne", "La minuterie du palier ne s'allume plus au 4e étage."),
    ],
    "hvac": [
        ("Climatisation bruyante", "Le climatiseur de la chambre fait un bruit anormal."),
        ("Chauffe-eau en panne", "Plus d'eau chaude depuis ce matin."),
    ],
    "elevator": [
        ("Ascenseur bloqué", "L'ascenseur reste bloqué au 2e étage, portes fermées."),
        ("Bouton d'appel cassé", "Le bouton d'appel du rez-de-chaussée ne répond plus."),
    ],
    "cleaning": [
        (
            "Escaliers non nettoyés",
            "Les escaliers du bâtiment n'ont pas été nettoyés cette semaine.",
        ),
        ("Local poubelles malodorant", "Odeurs fortes au local poubelles, conteneurs débordants."),
    ],
    "security": [
        ("Porte du parking ouverte", "La porte du parking reste ouverte en permanence."),
        ("Caméra du hall hors service", "L'écran de la loge n'affiche plus la caméra du hall."),
    ],
    "common_areas": [
        ("Arrosage du jardin défaillant", "Une partie du gazon jaunit, l'arrosage ne passe plus."),
        ("Carreau cassé dans le hall", "Un carreau de la vitre d'entrée est fissuré."),
    ],
    "noise": [
        (
            "Nuisances sonores nocturnes",
            "Musique forte au-dessus de chez moi après minuit plusieurs soirs.",
        )
    ],
    "information": [
        (
            "Date de la prochaine AG",
            "Pouvez-vous me confirmer la date de la prochaine assemblée générale ?",
        )
    ],
    "suggestion": [
        ("Installer un abri vélos", "Il serait utile d'installer un abri vélos près de l'entrée.")
    ],
}

WORK_ORDERS = [
    ("preventive", "Vérification des extincteurs", "Contrôle annuel et recharge si nécessaire."),
    (
        "preventive",
        "Nettoyage des gaines de ventilation",
        "Nettoyage des VMC des parties communes.",
    ),
    (
        "inspection",
        "Inspection de la toiture-terrasse",
        "Contrôle de l'étanchéité avant la saison des pluies.",
    ),
    (
        "corrective",
        "Remplacement de la pompe du surpresseur",
        "La pompe principale présente des fuites.",
    ),
    (
        "corrective",
        "Réparation du portail automatique",
        "Le moteur du portail force à la fermeture.",
    ),
    ("cleaning", "Nettoyage haute pression du parking", "Nettoyage complet des niveaux -1 et -2."),
    (
        "renovation",
        "Peinture de la cage d'escalier",
        "Reprise des murs et plafonds du rez-de-chaussée au 3e.",
    ),
    (
        "inspection",
        "Contrôle des détecteurs de fumée",
        "Vérification des détecteurs des parties communes.",
    ),
]

LISTINGS = [
    (
        "real_estate_rental",
        "Appartement 3 pièces meublé",
        "Bel appartement lumineux, cuisine équipée, deux chambres, balcon avec vue sur le jardin.",
        "9500.00",
    ),
    (
        "real_estate_sale",
        "Appartement 110 m² à vendre",
        "Traversant, trois chambres, deux salles de bain, place de parking et cave.",
        "1850000.00",
    ),
    (
        "real_estate_rental",
        "Studio à louer",
        "Studio rénové idéal étudiant ou jeune actif.",
        "4200.00",
    ),
    ("various_offer", "Vélo enfant 16 pouces", "Très bon état, petites roues fournies.", "450.00"),
    (
        "various_offer",
        "Canapé d'angle gris",
        "Canapé convertible, housse lavable, 3 ans.",
        "3500.00",
    ),
    (
        "various_offer",
        "Cours de soutien en mathématiques",
        "Professeur certifié, collège et lycée, à domicile.",
        "150.00",
    ),
    (
        "various_offer",
        "Table à manger et 6 chaises",
        "Bois massif, quelques traces d'usage.",
        "2800.00",
    ),
    ("various_offer", "Poussette double", "Utilisée un an, avec habillage pluie.", "1200.00"),
    (
        "various_offer",
        "Garde d'enfants le soir",
        "Étudiante sérieuse, disponible en semaine.",
        None,
    ),
    (
        "real_estate_rental",
        "Place de parking à louer",
        "Place couverte au niveau -1, accès badge.",
        "600.00",
    ),
]

CHAT_LINES = [
    "Bonjour, je vous confirme la prise en charge de votre demande.",
    "Merci ! Quand pouvez-vous passer ?",
    "Le technicien passera demain entre 10h et 12h.",
    "Parfait, je serai présent.",
    "C'est réparé, pouvez-vous vérifier de votre côté ?",
    "Tout fonctionne, merci beaucoup pour la réactivité.",
    "Pouvez-vous m'envoyer une photo du problème ?",
    "Voici la photo, la fuite est au niveau du joint.",
]

VISIT_REASONS = [
    "Visite familiale",
    "Livraison",
    "Intervention technique",
    "Visite d'un ami",
    "Aide à domicile",
    "Déménagement",
    "Visite d'appartement",
    "Coursier",
]
