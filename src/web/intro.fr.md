# Le projet

## Pourquoi ?

En 1984 je découvre le livre "The hobbit" vendu avec le jeu éponyme pour Oric Atmos.
Je n'ai jamais réussi à terminer le jeu mais je garde encore aujourd'hui,
42 après, un souvenir imperissable de ce jeu absolument avant gardiste pour l'époque.

Parler à des personnages ? Des personnages autonomes ?
Un logiciel capable de comprendre des phrases complexes ?
Rien de tout cela n'existait à l'époque et pourtant ils l'ont fait.

Vers 2004, puis 2014, j'ai eu la chance de pouvoir échanger
par mail avec Veronika Megler (co développeuse avec Philip Mitchell) où je lui ai exprimé
ma gratitude pour ce fabuleux jeu.

Il s'agit ici de la version originale du port Oric Atmos (réalisé vers 1983 par Gregg Barnett) dont le fonctionnement a été analysé
afin de permettre la visualisation en temps réel de la logique interne du jeu.

Ce que vous avez ici est l'exécution du code d'origine, sans aucune modification.
Le code ne s'exécute pas dans un émulateur Oric
mais dans le simulateur 6502 "sim65" de la suite cc65 grace aux mécanismes
de "para virtualisation" de sim65.

## Comment ?

70% de la rétro ingéniérie a été réalisée par IA seule.

La finalisation étant relativement
laborieuse j'ai ensuite inclus les projets "Wilderland" (Valerio Messina)
et "The Hobbit ZX Spectrum disassembly" (Paul Maddern) dans l'analyse IA
comme source complémentaire de documentation (variables manquantes, corrélation
des lieux, etc).

## Graphismes

Les illustrations ont été transformées en SVG à partir des données vectorielles encodées
dans le binaire du jeu.
