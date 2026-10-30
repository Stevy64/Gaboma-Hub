# Vérification de livraison — 27 octobre 2026

## Résultats

- Django : 55 tests réussis, aucune erreur du contrôle système.
- Migrations : aucune modification de modèle non enregistrée.
- Finitions graphiques : filets de section, bannière créateur, Hero éditorial et fil d'Ariane
  des pages intérieures contrôlés ; formulaire de connexion vérifié dans le navigateur.
- Base locale initialisée : six applications, aucun compte par défaut.
- Navigateur : nouvelle Hero gabonaise, catalogue mobile, filtres et fiches avec section des avis vérifiés.
- Interface : bleu, blanc et orange ; navigation tactile en bas sur mobile.
- Direction éditoriale : en-tête avec monogramme, Hero et illustration vectorielle, filets de
  séparation numérotés, en-tête du catalogue et bannière pour les créateurs. Les vues de compte,
  les fiches et les formulaires reprennent cette charte.

## Parcours vérifiés automatiquement

Carrousels limités aux applications publiées, classement communautaire basé uniquement sur les
avis visibles, absence de carrousels non filtrés pendant la recherche et dans les favoris.
Les parcours de comptes, formulaires, médias, avis et paiements continuent à passer.

Vérifications navigateur : défilement du carrousel, cartes compactes en grille sur mobile,
affichage/masquage d'un champ de mot de passe vide, icônes de formulaire et absence de chargement
bloqué lorsqu'un champ obligatoire n'est pas rempli. Sur l'écran de contrôle, les cartes de la
grille mesuraient 184 à 200 px de haut selon la longueur du nom, et les lignes du mode liste
environ 115 px. Aucune erreur JavaScript n'a été relevée pendant ce contrôle. La hauteur reste
adaptative ; elle n'est pas coupée de force.

Affichage liste/grille, conservation des filtres dans les liens du sélecteur, préférence de
session, activation et désactivation du fond du Hero, téléversement des visuels depuis
l'administration, accès réservé au personnel autorisé, emplacements publicitaires, exclusion
des campagnes désactivées, expirées, futures ou sans image, dates incohérentes et liens invalides.
Le toggle a également été contrôlé dans le navigateur sur écran étroit : deux colonnes
en grille et retour à une colonne en liste.

Ajout du logo et de la bannière, obligation des deux images sur les nouvelles fiches,
refus des faux fichiers et des images de plus de 5 Mo, conversion WebP, conservation des
médias existants, notes limitées à 1–5, mise à jour d'un seul avis par personne, commentaires
échappés, suppression de son propre avis, avis masqués exclus des moyennes et du classement,
protection de la publication d'avis par connexion et CSRF.

Catalogue public et filtres, favoris, inscription, protection CSRF, isolation des fiches
et paiements entre utilisateurs, ajout gratuit par l'administration, refus de publication
d'une fiche utilisateur non payée, tarif serveur de 2 000 FCFA, réutilisation du paiement
en cours, retour navigateur non probant, signature des notifications, vérification distante
du montant et de la référence, refus d'un identifiant de transaction réutilisé, traitement
idempotent, passage en modération après paiement et absence de réactivation d'une fiche archivée.

Les tests de paiement utilisent des réponses SingPay simulées. Aucun débit réel n'a été effectué.
Le hachage rapide des mots de passe est limité aux tests ; l'application utilise les protections
normales de Django.

## À terminer avec le compte marchand

Renseigner les clés privées dans `.env`, configurer l'adresse HTTPS de notification dans le
portefeuille SingPay, puis effectuer un essai complet avec le prestataire. Vérifier l'ouverture
du paiement, le succès, l'annulation et le retour de notification. Publier ensuite la fiche
depuis l'administration. Le README décrit la configuration et les limites du fonctionnement
en local pour les notifications externes.

## Contenu de l'archive

Sources Django, migrations, tests, modèles de pages, styles, lanceurs locaux, dépendances et
documentation. L'archive exclut les clés privées, la base locale, les comptes et l'environnement
Python installé. Le premier lancement crée ces éléments sur la machine de destination.

### Actualisation visuelle — 28 octobre 2026
55 tests Django réussis. Accueil mobile et catalogue vérifiés dans le navigateur ; cartes de 183 à 201 px, aucun débordement horizontal de page, bascule en liste fonctionnelle.

### En-tête et contrôle fonctionnel — 28 octobre 2026
Fond de l’en-tête bord à bord et contenu centré ; contrôles navigateur aux largeurs CSS observées de 327, 767, 1309 et 1745 px : aucun débordement horizontal, bord gauche à zéro et bord droit à la largeur utile. Recherche réelle et compteur de résultats vérifiés, carrousel mobile, fiche publique et validation de connexion vérifiés. Aucun indicateur bloqué après navigation ou formulaire invalide. Console sans erreur. Aperçu de fichier supprimé lors d’une sélection vide/invalide. Réduction des mouvements conservée. Les 55 tests passent, avec assertions supplémentaires pour le compteur filtré ; syntaxe JavaScript et migrations vérifiées. Les paiements SingPay restent testés par simulation, sans transaction réelle.

### Visuels et en-tête intelligent
Bannières au ratio 2:1 ; logos 46 px sur mobile et 54 px sur ordinateur. Contrôle navigateur : en-tête mobile 70 px au repos puis 56 px au défilement ; ordinateur 60 px en mode compact, toujours à top=0. Retour en haut rétablit la taille normale. Aucun débordement horizontal observé. Écouteur passif avec requestAnimationFrame, seuils distincts évitant les oscillations, réduction des mouvements respectée. Syntaxe JavaScript vérifiée.


### Vitrine administrable et filtres — 28 octobre 2026
60 tests Django réussis. Migration 0004 appliquée localement, aucune migration en attente. Tests ajoutés : upload d'une publicité en vitrine avec conversion WebP, ordre et plages de diffusion, exclusion des éléments désactivés, réglages des textes et sections, échappement HTML, validation du tarif, accès admin, tarif personnalisé non falsifiable et figé sur chaque fiche, confirmation SingPay simulée au montant personnalisé. Les paiements réels ne sont pas testés.
Contrôles navigateur : vitrine de secours avec trois applications, passage de 1/3 à 2/3 ; filtres repliables, application de la catégorie Analyses sportives donnant 1 résultat ; remise à zéro ; bascule grille/liste ; aucun débordement horizontal sur mobile et ordinateur. Console sans erreur et indicateur de chargement masqué après navigation.

### Refonte UX inspirée de Go Design
60 tests réussis après modification des gabarits. Vérification des cartes mobiles, de la fiche Gab Event, de son lien vers les avis et des dimensions mobile/ordinateur ; aucun débordement horizontal observé. Les médias uploadés conservent leur affichage ; seule la présentation de remplacement sans bannière utilise un logo central.


## Grille et menus — 28 octobre 2026
Grille vérifiée à 391, 909 et 1309 px : respectivement 2, 3 et 4 colonnes, sans débordement horizontal. Visuels sur toute la largeur des cartes. Sélecteurs personnalisés : choix au clic, navigation clavier et application du filtre Analyses sportives avec tri par note vérifiés. Les 60 tests Django passent.


## Console et soumission — 29 octobre 2026
69 tests passent, dont permissions du tableau de bord, refus du compte de démonstration en production et coches selon l’état réel de la soumission. Connexion admin locale vérifiée. Tableau de bord et liste des applications contrôlés ; en-tête et débordements vérifiés sur mobile. Accès marchand vérifié en lecture seule (HTTP 200, environnement sandbox), sans initier de paiement.

## Administration mobile / K3s — 29 octobre 2026

77 tests Django réussis (PostgreSQL/Redis), dont droits lecture seule, CSRF, validation prestataire, montant incorrect, publication bloquée et historique. Navigation, filtre À valider et détail contrôlés à 390 et 1280 pixels ; aucun débordement horizontal ; thème sombre contrôlé. 15 ressources Kubernetes validées strictement avec kubeconform. Configuration Nginx testée en UID 10001. Séquencement du script testé avec succès et échec de migration simulés. Aucun déploiement réel, aucun DNS modifié, aucun paiement réel.

## Paiement manuel et gestion des volumes
91 tests réussis après ajout de la validation manuelle ; 14 tests du parcours réexécutés après conservation des filtres et pagination de l’historique. Confirmation sans tentative en ligne, confirmation d’une tentative existante, doublon de reçu, montant incorrect, accès non autorisé et publication vérifiés dans la base de tests isolée. Formulaire manuel et filtres inspectés à 390 px sans débordement. Aucun paiement réel modifié. Migration 0007 appliquée localement.
