# Le projet

## Pourquoi ?

En 1984 je découvre le livre "The hobbit" vendu avec le jeu éponyme pour Oric Atmos.
Je n'ai jamais réussi à terminer le jeu mais je garde encore aujourd'hui,
42 ans après, un souvenir impérissable de ce jeu absolument avant-gardiste pour l'époque.

Parler à des personnages ? Des personnages autonomes ?
Un logiciel capable de comprendre des phrases complexes ?
Un mini monde chaotique dans lequel chaque partie était différente.
Rien de tout cela n'existait à l'époque et pourtant ils l'ont fait.

Vers 2004, puis 2014, j'ai eu la chance de pouvoir discuter
par mail avec Veronika Megler (co développeuse avec Philip Mitchell) où je lui ai exprimé
ma gratitude pour ce fabuleux jeu, le seul qu'elle ait jamais développé, le reste de sa carrière
s'étant faite chez IBM.

Il s'agit ici de la version originale du port Oric Atmos (réalisé vers 1983 par Gregg Barnett) dont le fonctionnement a été analysé
pour permettre la visualisation en temps réel de la logique interne du jeu.

Ce que vous avez ici est l'exécution du code d'origine, sans aucune modification.
Le code ne s'exécute pas dans un émulateur Oric
mais dans le simulateur sim65 de la suite cc65 grace aux mécanismes
de "paravirtualisation" de sim65.

## Comment ?

70% de la rétro ingéniérie a été réalisée par une paire d'IA.

La finalisation de la documentation étant relativement
laborieuse j'ai ensuite inclus dans la boucle d'analyse IA 'les projets "Wilderland" (Valerio Messina)
et "The Hobbit ZX Spectrum disassembly" (Paul Maddern)
comme sources complémentaires (variables manquantes, corrélation
des lieux, etc).

## Graphismes

Les illustrations ont été transformées en SVG à partir des données vectorielles encodées
dans le binaire du jeu.
