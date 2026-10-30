# Gaboma Hub — direction visuelle

## Intention

Une vitrine éditoriale des créateurs gabonais. Le visiteur doit identifier les applications,
comprendre les sections et rejoindre un service rapidement. La mise en page reste prioritaire
sur les effets décoratifs.

## Langage visuel

- Fond papier clair : `#f8f7f3`.
- Encre marine : `#203d52` ; bleu d'action : `#2758d7`.
- Cuivre : `#df8950`, réservé aux accents et repères.
- Identité gabonaise : drapeau discret et textes de marque ; aucune certification inventée.
- Typographie : Manrope pour la structure et les titres, DM Sans pour l'interface, Georgia
  italique pour quelques mots de marque. Les accents typographiques restent rares.

## Composition

Le Hero associe un titre éditorial, une action principale et une application réelle mise en
vitrine. L'illustration vectorielle « Connexions » est un dessin de marque, pas une capture
de l'application. Une bannière fournie remplace automatiquement ce visuel.

Les carrousels commencent par un filet fin et un numéro de section. Le catalogue utilise un
en-tête distinct « Le répertoire ». La bannière pour les créateurs adopte une composition
marine et cuivre, avec un lien clair vers la soumission et son tarif réel.

Les cartes gardent un format compact. Les visuels de remplacement utilisent une composition
typographique ; une bannière téléversée s'affiche à leur place. Les informations complètes
restent sur les fiches. Les ombres, les dégradés et les pastilles décoratives sont limités.

## Continuité

Les pages intérieures commencent par un fil d'Ariane discret et un intitulé de rubrique
(compte, répertoire ou espace créateur). Les titres conservent un poids modéré, les formulaires
un filet cuivre, et les panneaux secondaires une bordure commune. Ces repères permettent de
passer d'une page à l'autre en gardant la même identité.

Les séparateurs du catalogue et des carrousels reposent sur l'alignement, les filets et les
libellés. Les bannières réservent le contraste marine/cuivre à la mise en avant d'une app ou
à l'invitation destinée aux créateurs. Les libellés utilitaires et les zones tactiles restent
lisibles et accessibles même lorsque la composition est dense.

Les formulaires, les fiches, la modération visible, le suivi des paiements et la navigation
reprennent les mêmes couleurs, bordures et arrondis. Les icônes locales gardent un rôle
fonctionnel. Les animations courtes et les préférences de réduction des mouvements restent
prises en charge.

Les règles de cette direction sont regroupées dans `static/hub/editorial.css`. Le fichier
`static/hub/images/connections.svg` contient l'illustration de marque. La configuration du
fond du Hero, les publicités et les médias des applications restent gérés par l'administration.

## Actualisation du 28 octobre 2026

La couche finale `refinements.css` adopte un fond blanc bleuté, un bleu franc #235ce7 et des accents orange. Le Hero utilise une typographie sans empattement et un texte plus direct. Les cartes gardent leur format compact avec un bouton bleu clair, et la navigation mobile signale la rubrique active en bleu plein. Les bandeaux redondants sont retirés pour donner la priorité aux applications.

## Vitrine et filtres
La référence mobile fournie inspire une recherche dominante, des filtres secondaires repliables et des catégories orange douces. La vitrine native à défilement horizontal présente un visuel à la fois avec compteur et commandes accessibles. Les visuels publicitaires restent entiers (contain), les annonces sont identifiées comme publicités. Aucun défilement automatique.

## Cartes produit et fiches — référence Go Design
Cartes blanches avec visuels légèrement en retrait, logo central lorsque la bannière est absente, titres dégagés et actions pêche/orange. Les bannières téléversées sont conservées. Navigation mobile avec sélection douce, panneau récapitulatif des fiches, action principale orange et raccourcis Présentation / Notes et avis. Formulaires et avis harmonisés sur des surfaces claires.

Les actions des cartes « Ouvrir » et « Voir le projet » utilisent un fond bleu clair #eaf1ff et un texte bleu #235acb. La navigation mobile active reprend ces couleurs, avec un point orange #ee883e conservé.
