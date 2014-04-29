
# svnmerge2.py
**svnmerge2.py** est un outil permettant la gestion des branches, facilitant les opérations de fusion des commits. Il
permet de réduire le nombre d'erreurs de fusion et reste compatible avec l'utilisation de *TortoiseSVN*. Cet outil a été
développé en partant de l'outil **svnmerge.py** de orcware, [disponible ici](https://www.orcaware.com/svn/wiki/Svnmerge.py).
Cependant, il ne fonctionne pas tout à fait pareil et voici les principales différences :

* pas besoin d'effectuer la commande d'initialization ; vous pourrez commencer à utiliser svnmerge2.py à tout moment,
même si vous effectuez vos opérations de maintenance depuis des années avec TortoiseSVN ou avec la ligne de commande SVN
ou tout autre outil,

* vous pouvez fusionner des commits en provenance de toute nouvelle branche, à condition, biensur, que cette branche ait
un historique commun avec la branche de destination,

* l'outil présente les commits d'une manière intéractive, inspirée du fonctionnement de *git --interactive* ; un menu est
présenté, permettant de choisir les commits pour prise en compte lors de la fusion ; dans les fait, cet outil permet de
faire des cherry-pick, terme utilisé toujours dans le monde *git*.

* le menu intéractif permet de marquer certains commits pour être ignorés ; ces commits n'apparaîtront plus dans les
listes intéractives et réduiront ainsi le risque de fausses manipulations.

L'outil **svnmerge2.py** n'effectue jamais de commit. Ceci est laissé à votre latitude. Pour vous aider, **svnmerge2.py**
génère automatiquement un fichier texte, qui peut être utilisée comme source pour le message de commit, que vous ferez
vous même en dehors de l'outil. Voir le mode opératoire plus bas.

# Installation
## Pré-requis
L'outil est écrit en python3, dont vous devez disposer sur votre système. En plus de python3, vous devez vous assurer que
vous disposez des modules suivants : xml.dom, pysvn, urllib et colorama. Le répertoire où se trouve l'exécutable python3
doit se trouver dans le PATH système ou utilisateur.

## Invocation de l'outil **svnmerge2.py**
Poser le script dans un répertoire à votre convenance, puis invoquez l'outil ainsi :

*Sous Windows*

    python3 svnmerge2.py

*Sous Linux*

    chmod +x svnmerge2.py  # ceci est nécessaire uniquement la première fois après l'installation
    ./svnmerge2.py

Sous Linux, vous pouvez lancer le script de n'importe quel répertoire à condition de le déposer dans un répertoire qui
se trouve sur le PATH. Dans ce cas, le préfixe ./ est inutile (mais vous saviez déjà cela). Toujours sous Linux, si vous
trouvez que taper **svnmerge2.py** est un peu long, vous pouvez toujours créer un lien symbolique ou un alias pour la
commande. Par exemple, vous pouvez ajouter ceci dans votre fichier *.bashrc*

    alias svnmerge='svnmerge2.py'

En absence de paramètres, l'outil devrait produire une sortie qui ressemble à ceci :

    usage: svnmerge [-h] [--verbose VERBOSE] sourcepath
    svnmerge: error: the following arguments are required: sourcepath

Ceci est signe que l'outil a bien été installé et que la configuration python3 est bien fonctionnelle ! Vous pouvez
maintenant passer à son utilisation.

# Fonctionnement
## Au préalable
Supposons que vous travaillez sur un projet qui dispose d'une branche de développement (habituellement nommée trunk) et
que vous maintenez en parallèle une branche qui sert de base pour les livraisons des versions successives. Cette branche
est initialement issue de la branche de développement (le trunk) et elle sert de branche d'intégration. Vous souhaitez
reporter périodiquement des commits de la branche de développement (trunk) sur cette branche.

Vous disposez sur votre poste de travail d'une copie locale de la branche d'intégration. **Cette copie locale doit être
propre et ne pas comporter des modifications non-commitées**. Si tel n'est pas le cas, un message d'erreur est affiché
lors de l'invocation de l'outil.

**IMPORTANT** : Si le répertoire courant n'est pas une copie locale *subversion*, l'outil quitte avec un message d'erreur.

## Si la branche d'intégration n'a jamais été fusionnée avec la branche de développement

    cd copie-locale-integration
    svnmerge2.py <url-svn-branche-dev>

Suivre les instructions à l'écran pour fusionner les commits ou encore pour marquer les commits inutiles en tant
qu'ignorés. Le mode opératoire est donnée plus bas.

## Flot de travail habituel

    cd copie-locale-integration
    svnmerge2.py ?

Un premier menu vous invite à choisir la branche d'où vous souhaitez prendre les commits. Taper le numéro de la ligne qui
contient la branche source, puis faites entrée pour arriver au menu principal. Voir le mode opératoire plus bas.

## Mode opératoire du menu principal

Le menu principal du script ressemble à ceci :

    1. R12345 <date du commit> <auteur1> Message du premier commit
    2. R12355 <date du commit> <auteur2> Message du second commit
    ... d'autres lignes qui ressemblent à ces deux premières, numérotées en séquence

    D montre/cache les détail des fichiers | F Marquer pour fusion... | I Marquer pour ignorer... | Q Quitter

Sur un terminal couleurs, les différentes zones sont identifiées par des couleurs différentes. Les lignes numérotées
montrent les commits disponibles sur la branche source et qui n'ont pas été encore fusionnées sur la branche qui
correspond à la copie locale où le script s'exécute. La dernière ligne présente les options dont vous disposez pour
opérer plus loin :

* **D** permet de réafficher la liste des commits, mais avec le détail des fichiers touchés par chacun des commits ; ces
fichiers ne sont pas affichés d'emblée pour ne pas trop charger l'affichage. Une fois l'affichage des fichiers activé,
il est possible de revenir au mode bref par une nouvelle exécution de cette commande

* **F** débute l'opération de fusion

* **I** débute l'opération de mise sur la liste des commits ignorés

* **Q** quitte le script immédiatement. Un message est émis si la copie locale a été modifiée. Aussi, la copie locale
contient un nouveau fichier nommé *commit_message*, dont le contenu peut être utilisé lors de l'invocation de la commande
 *svn commit*. Voir plus loin un exemple d'utilisation de ce fichier.

Pour exécuter l'une de ces opérations, tapez la lettre respective, puis faites *Entrée*.

### Functionnement de la commande **F**
Il faut d'abord choisir la liste des commits, par rapport à la liste de commits affichée précédemment par l'outil :

    Entrer les numéros des commits (p.ex. 1,3-5,8) :

Tapez les numéros de commits comme indiqué, puis faites entrée pour produire le réaffichage du de la liste des commits
et d'un nouveau menu, différent. Les lignes correspondantes aux commits choisis vont être signalées avec des astérisques.

Un nouveau menu apparait sur la dernière ligne :

    V Valider le choix | F Marquer d'autres lignes... | D montre/cache les détail des fichiers | Q Quitter

Les options de ce menu sont :

* **V** Si tous les commits que vous intentionnez de reprendre sont bien marqués, cette commande permet de passer à la
fusion effective. La copie locale est impactée une fois cette commande lancée. Cette commande parcourt la liste des
commits marqués, puis, pour chaque commit, effectue :

        svn merge -cNNNN --depth=infinity <svn-url-branche-source>
        ajout d'une ligne dans le fichier *commit_message*

Une fois la liste de commits parcouroue, l'outil revient au menu principal. S'il ne reste plus de commits disponible,
alors la liste des commits est remplacée avec un message correspondant, et le menu principal ne donne que l'option **Q**
pour quitter.

* **F** Permet de marquer d'autres lignes, pour le cas où vous vous rendez-compte que tous les commits que vous comptez
fusionnés n'ont pas été marqués.

* **D** Permet l'affichage des fichiers impactés par les commits, s'agissant de la même commande que celle du niveau du
menu principal.

* **Q** Permet de quitter immédiatement l'exécution du script.

### Fonctionnement de la commande **I**

L'utilisation de cette commande pose une propriété spéciale nommée **svnmerge:ignored_commits** sur la branche
correspondant à la copie locale. Cette information est lue à chaque fois que la liste des commits doit être construite
et affichée et permet de filtrer les commits qui ne doivent plus être pris en compte.

Par exemple, si vous avez déjà effectué des reports de code avec un outil extérieur, tel que KDiff3, effectuer un
*svn merge* va produire à coup sur un conflit. Pour éviter cela, il convient de marquer le commit correspondant en tant
que commit ignoré, et le risque de provoquer des conflits de ce type est éliminé.

La commande commence par demander le numéro de commit, comme dans les autres cas :

    Entrer les numéros des commits (p.ex. 1,3-5,8) :

La liste des commits sera réaffichée, avec les lignes choisies marquées avec des astérisques. La dernière ligne montre
le menu suivant :

    Lignes marquées pour être IGNOREES
    V Valider le choix I Marquer d'autres lignes... D montre/cache les détail des fichiers | Q Quitter

Les options de ce menu sont :

* **V** Finaliser l'opération et modifier la propriété **svnmerge:ignored_commits**. Le fichier **commit_message** est
également renseigné et peut être utilisé pour commiter le changement de la propriété. Tant que le commit n'est pas
effectuée, cette propriété n'est modifiée que localement et d'autres postes de travail ne pourront pas la récupérer.

* **I** Permet de marquer d'autres lignes

* **Q** Permet de quitter le script immédiatement

## Commiter les changements

Un autre bout de script utile sous Linux est ceci, qui pourrait être nommé, par exemple, *svnmerge-commit* :

    #!/bin/bash
    svn commit -F commit_message
    rm commit_message
