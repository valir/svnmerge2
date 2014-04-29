# svnmerge2.py
**svnmerge2.py** is a tool for automatic branch management, inspired from the original [svnmerge.py tool](https://www.orcaware.com/svn/wiki/Svnmerge.py)
It helps reduce merging errors and it's compatible with other tools such as *TortoiseSVN*.

**svnmerge2.py** differs from the original *svnmerge.py* tool in several ways:
* it won't require an "init" step. **svnmerge2.py** will start merging your branches right away
* it uses the *svn:mergeinfo* automatically, so it can be used in conjunction with other tools, like TortoiseSVN
* it sports an interactive menu, similar to git --interactive
* it maintains an ignore list where you can add commits you'll never want to get merged from the source branch0
* uses internationalization, so it could be largely used *(Feature yet to be done)*

*svnmerge2.py* (the tool) will never commit changes to the central repository. That's your responsibility, after
checking the issue of the tool's execution. However, the tool will assist by automatically creating a text file you can
use as a commit message source.

# Installing
## Dependencies
The tool needs python3, which must be installed somewhere on your system's PATH. Make sure you also add the following
modules: xml.dom, pysvn, urllib and colorama.

## Invoking **svnmerge2.py**
Poser le script dans un répertoire à votre convenance, puis invoquez l'outil ainsi :
Download the script in a directory of your choice then launch it:

*Windows boxes*

    python3 svnmerge2.py

*Linux boxes*

    chmod +x svnmerge2.py  # this is needed only the first time, after downloading the script, it it's not already executable
    ./svnmerge2.py

On Linux boxes, you may put the script in any directory listed in the $PATH variable. In that case, the ./ prefix is no
longer needed (but you already knew that ;-). Always under Linux, you may also define a symlink or an alias named
*svnmerge*, if you find *svnmerge2.py* a little too long to type.

    alias svnmerge='svnmerge2.py'

When launched without parameters, the tool should produce an output such as this:

    usage: svnmerge [-h] [--verbose VERBOSE] sourcepath
    svnmerge: error: the following arguments are required: sourcepath

That means that the tool is ready to use, so move on to the next section.

# Operating the script
## Before you start
Suppose you're working on a project that has a development branch (such as the trunk) and you're maintaining another branch
which is used when delivering the successive versions. That branch was derived from the development branch and it's used
for integration builds. You want to periodically merge commits from the development branch to the integration branch.

You have an integration branch local copy on your computer. **This local copy must absolutely be clean and it should not
have locally added files or other modification whatsoever**. If that's not the case, the tool will issue an warning when
launched.

**IMPORTANT** : If the current directory is not an SVN local copy, it prints an error message that it quits.

## If the integration branch was never merged with the development branch

    cd integration-local-copy
    svnmerge2.py <url-svn-dev-branch>

Suivre les instructions à l'écran pour fusionner les commits ou encore pour marquer les commits inutiles en tant
qu'ignorés. Le mode opératoire est donnée plus bas.

Let the tool guide you through the process of merging or marking the unneeded commits. The steps are detailed below.

## Usual workflow

    cd integration-local-copy
    svnmerge2.py ?

The tool will display a first menu, inviting you to choose the source branch you want to get merged into the current
branch. Just enter the corresponding line number, the hit enter to get to the main menu. See description below.

## Using the main menu

The main menu looks like this:

    1. R12345 <commit date> <auteur1> First commit message
    2. R12355 <commit date> <auteur2> Second commit message
    ... other similar lines, each having a sequence number

    D show/hide file details | M Select commits for merge... | I Select commits to ignore... | Q Quit

If you're using a color terminal, the different menu fields are individually colored. The numbered lines display the
 commits available on the source branch that are not yet merged on with the local copy. The last line show the available
 options:

* **D** toggle the file details for each commit; this detail is initially hidden to avoid display cluttering.

* **M** Start the merge operation

* **I** start the ignore operation

* **Q** immediately quit the script. A message will be printed upon exit if the local copy was modified. If that's the
 case, the tool will also produce a new file named *commit_message* that contains a commit message you can use when
 committing your local copy. See below for an usage example.

In order to start one of these commands, simply enter the corresponding letter (the case is ignored) the hit *enter*.

### The **M** command
The tool will first ask to select the line numbers:

    Enter commit numbers (ex: 1,3-5,8):

Enter the commit numbers using the example syntax, the hit *enter* to get the menu redisplayed. This time, the selected
lines will display a star as the very first character.

A new menu will be displayed:

    V Validate | M Select more commits... | D show/hide file details | Q Quit

This menu's options are:

* **V** Use this when all commits are marked and you want to go ahead and validate your choice. The tool will effectively
 do the merge and your local copy will get modified. For each of the marked commits the tool will do:

        svn merge -cNNNN --depth=infinity <svn-url-source-branch>
        Add a corresponding line to the file named *commit_message*

Once the commit list done, the tool goes back the the main menu. If no commits are left unmerged, the available commit
list will be replaced with an "no commit available" message, and the main menu will only give you the choice to quit.

* **M** Let's you select other lines, and add them to the list of the commits to be processed.

* **D** toggle the file details for each commit; this detail is initially hidden to avoid display cluttering. That's the
 same option as the one from the main menu.

* **Q** Immediately quits the script.

### The **I** command

This command creates a special property on your local copy, named **svnmerge:ignored_commits**. This will get transmitted
to the SVN repository along with your commit, so other team members will also benefit from it. The tool reads this property
upon start and uses it to filter the commit list displayed by the main menu.

This options comes in handy when you already merged code using external tools, such as KDiff3, and doing and *svn merge*
would lead to a conflict. To avoid that, you put the corresponding commit on this ignore list and you eliminate the risk
of conflicting merging.

La commande commence par demander le numéro de commit, comme dans les autres cas :
The tool starts by asking the commit number:

    Enter commit numbers (ex: 1,3-5,8):

The commits list will be refreshed, with selected lines marked by a star. The menu will display the following commands:

    Lines marked to be IGNORED
    V Validate I Add other lines... D show/hide file details | Q Quit

This menu options are:

* **V** Go ahead and put the selected lines on the ignore list **svnmerge:ignored_commits**. The file **commit_message**
   will aso be created and it can be used to commit the property change. As long as this property is not committed, other
   team members will not get it on their local copies.

* **I** Add other lines to the ignore list

* **Q** Immediately quit the script

## Commit the changes
You could use the following little script when you're done with the merging operation:

    #!/bin/bash
    svn commit -F commit_message
    rm commit_message
