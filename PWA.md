# PWA et cache de performance

Le Hub reste installable depuis `/installer/` avec une connexion HTTPS (localhost accepté en développement). Android propose le bouton natif lorsqu’il est disponible ; sur Safari iOS, utiliser Partager → Sur l’écran d’accueil.

Le catalogue, les comptes et toutes les opérations nécessitent Internet. Il n’y a plus de bibliothèque locale, de copie du catalogue, de consultation hors ligne ou de repli de navigation.

Le service worker conserve uniquement les ressources GET `/static/hub/` : styles, scripts, icônes. Les fichiers de production à empreinte sont servis depuis le cache ; les autres sont revalidés en arrière-plan. Cache limité à 80 ressources de 1 Mo maximum chacune. Les préférences jour/nuit et d’affichage restent conservées selon leur mécanisme existant. Les médias utilisent le cache HTTP normal du navigateur.

À l’activation de cette version, les anciens caches Gaboma (catalogue, images et coque hors ligne) sont supprimés automatiquement. L’activation ne recharge pas les formulaires ouverts. Les anciennes pages déjà affichées disparaissent à la navigation suivante. Aucune donnée de compte ni paiement n’est ajoutée au cache. Le navigateur peut libérer les ressources selon l’espace disponible.

Les routes `/hors-ligne/` et `/pwa/catalogue.json` sont retirées et renvoient 404. La PWA installée reste valide avec le même identifiant et les mêmes icônes.
