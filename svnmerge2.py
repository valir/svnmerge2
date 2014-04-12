#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 Valentin Rusu <kde at rusu dot info>
# All rights reserved.
#
# Portions of this script (SvnLogParser) come from orcaware svnmerge
# https://www.orcaware.com/svn/wiki/Svnmerge.py
# Copyright (c) 2005, Giovanni Bajo
# Copyright (c) 2004-2005, Awarix, Inc.
# Copyright (c) Archie Cobbs <archie at awarix dot com>
# Copyright (c) Giovanni Bajo <rasky at develer dot com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#

import re
from subprocess import CalledProcessError
import sys
import subprocess
from xml.dom import pulldom
import pysvn
import argparse
from urllib.parse import urlparse
from colorama import init, Fore

OPT_SOURCEPATH = "sourcepath"
COMMIT_MESSAGE_FILE_NAME = "commit_message"

global opts


class SvnLogParser:
    """
    Parse the "svn log", going through the XML output and using pulldom (which
    would even allow streaming the command output).
    """

    def __init__(self, xml):
        self._events = pulldom.parseString(xml)

    def __getitem__(self, idx):
        for event, node in self._events:
            if event == pulldom.START_ELEMENT and node.tagName == "logentry":
                self._events.expandNode(node)
                return self.SvnLogRevision(node)
        raise IndexError("Could not find 'logentry' tag in xml")

    class SvnLogRevision:
        def __init__(self, xmlnode):
            self.n = xmlnode

        def revision(self):
            return int(self.n.getAttribute("revision"))

        def author(self):
            return self.n.getElementsByTagName("author")[0].firstChild.data

        def paths(self):
            return [self.SvnLogPath(n)
                    for n in self.n.getElementsByTagName("path")]

        def msg(self):
            try:
                return ''.join([c.data for c in self.n.getElementsByTagName("msg")[0].childNodes])
            except AttributeError:
                return "<pas de message de log :-( >"

        def date(self):
            return self.n.getElementsByTagName("date")[0].firstChild.data

        class SvnLogPath:
            def __init__(self, xmlnode):
                self.n = xmlnode

            def action(self):
                return self.n.getAttribute("action")

            def pathid(self):
                return self.n.firstChild.data

            def copyfrom_rev(self):
                try:
                    return self.n.getAttribute("copyfrom-rev")
                except KeyError:
                    return None

            def copyfrom_pathid(self):
                try:
                    return self.n.getAttribute("copyfrom-path")
                except KeyError:
                    return None


class Svn:
    @staticmethod
    def launch(s, show=False, pretend=False, **kwargs):
        """Launch SVN and grab its output."""
        global opts
        cmd = ['svn']
        if opts.get("username", None):
            cmd.append("--username=")
            cmd.append(opts["username"])
        if opts.get("password", None):
            cmd.append("--password=")
            cmd.append(opts["password"])
        if opts.get("config-dir", None):
            cmd.append("--config-dir=")
            cmd.append(opts["config-dir"])
        cmd.extend(s.split(' '))
        if show or opts["verbose"] >= 2:
            print(cmd)
        if pretend:
            return None
        return subprocess.check_output(cmd, **kwargs).decode()

    @staticmethod
    def svn_command(s):
        """Do (or pretend to do) an SVN command."""
        out = Svn.launch(s, show=opts["show-changes"] or opts["dry-run"],
                         pretend=opts["dry-run"],
                         split_lines=False)
        if not opts["dry-run"]:
            print(out)


class SvnMerge:
    """
        Cette class contient la logique principale du script
        Il s'agit d'une machine à état, dont l'état courant peut être l'une
        des constantes STATE_xxx
    """
    STATE_SHOW_AVAIL_COMMITS = 1
    STATE_MARK_FOR_IGNORE = 2
    STATE_MARK_FOR_COMMIT = 3
    STATE_NO_MORE_COMMITS = 4
    SVN_PROP_IGNORED_COMMITS = "svnmerge:ignored_commits"

    def __init__(self):
        self.source_branch = ''
        self.source_branch_url = ''
        self.available_commits = []
        self.ignored_commits = []
        self.merge_info_lines = []
        self.already_merged_commits = []
        self.loop_state = self.STATE_SHOW_AVAIL_COMMITS
        self.marked_commits = []
        self.commit_message = ''
        self.branche_connue = False
        self.local_copy_dirty = False
        self.repos_root_url = ''

    def check_local_copy(self):
        svn = pysvn.Client()
        info = svn.info2('')  # ceci plante si nous ne sommes pas dans un répertoire copie locale!
        url = info[0][1].URL
        rev = info[0][1].rev.number
        self.repos_root_url = info[0][1].repos_root_URL
        print(u"Copie locale URL=%s@%d" % (url, rev))

    @staticmethod
    def check_clean_local_copy():
        stat = Svn.launch("stat")
        if len(stat) > 0:
            print(Fore.RED + u"La copie locale présente des modifications:" + Fore.RESET)
            print(stat)
            choix = input(Fore.YELLOW + u"Continuer dans cet état ? [y/N] :" + Fore.RESET)
            if choix != 'y':
                sys.exit(1)

    @staticmethod
    def update_local_copy():
        print(u"Mise à jour de la copie locale...")
        up = Svn.launch("up")
        print(up)

    def read_already_merged_commits(self):
        self.already_merged_commits.clear()

        mergeprop = Svn.launch("propget svn:mergeinfo")
        if opts["verbose"] >= 2:
            print(mergeprop)
        self.merge_info_lines = mergeprop.split('\n')
        if '' in self.merge_info_lines:
            self.merge_info_lines.remove('')

        # si la branche source n'est pas encore connue, présente un menu pour la choisir
        srcpath = opts[OPT_SOURCEPATH]
        if len(self.source_branch) == 0:
            if srcpath == '?':
                # l'utilisateur désire choisir la branche
                if len(self.merge_info_lines) == 0:
                    print(
                        u"Vous avez indiqué le source '?' mais la copie locale correspond à une branche\nqui n'a jamais connu de fusion.\nVeuillez recommencer un indiquant l'URL d'une branche source.")
                    sys.exit(1)
                else:
                    print(u"Liste des branches connues pour la copie locale :")
                    branches = []
                    n = 1
                    for mi in self.merge_info_lines:
                        mi_branch, mi_recs = mi.split(':')
                        print((Fore.YELLOW + u"%d." + Fore.GREEN + " %s" + Fore.RESET) % (n, mi_branch))
                        branches.append(mi_branch)
                        n += 1
                    print("")
                    while 1:
                        try:
                            nb = int(input((Fore.YELLOW + u"Quel branche souhaitez choisir ? [1..%d] " + Fore.RESET) %
                                           (n - 1))) - 1
                            if 0 < nb < n:
                                self.source_branch = branches[nb]
                                self.source_branch_url = self.repos_root_url + self.source_branch
                                print(u"Branche choisie : %s" % self.source_branch_url)
                                break
                            else:
                                print("Le nombre doit aller de 1 à %d" % (n - 1))
                        except ValueError:
                            print(u"Veuillez introduire un numéro!")
            else:
                self.source_branch_url = srcpath
                self.source_branch = urlparse(srcpath).path

        # parcourt la liste des des branches jusqu'à trouver (ou pas) la branche indiquée par l'utilisateur
        self.branche_connue = False
        mi_revs = ''
        for e in self.merge_info_lines:
            if opts["verbose"] >= 2:
                print(e)
            mi_branch, mi_revs = e.split(':')
            if mi_branch == self.source_branch:
                self.branche_connue = True
                break
        if not self.branche_connue:
            print("Fusion d'une nouvelle nouvelle branche '%s'" % self.source_branch)
        else:
            mi_revs_list = mi_revs.split(',')
            for s in mi_revs_list:
                if s.find('-') > 0:
                    r = s.split('-')
                    for i in list(range(int(r[0]), int(r[1]) + 1)):
                        self.already_merged_commits.append(int(i))
                else:
                    self.already_merged_commits.append(int(s))
        if opts["verbose"] >= 2:
            print(self.already_merged_commits)

    def read_available_commits(self):
        # inutile d'afficher les commits précédents au début de la branche courante
        # ceci trouve donc le commit qui a créé la branche courante
        cur_branch_creat_rev = SvnLogParser(
            Svn.launch('log -v --xml -r0:HEAD --stop-on-copy --limit 1 .'))[0].revision()

        self.read_ignored_commits()

        # lecture de svn:mergeinfo
        # NOTE: cette propriété est également gérée par TortoiseSVN
        self.read_already_merged_commits()

        self.available_commits.clear()
        for cx in SvnLogParser(
                Svn.launch('log -v --xml --stop-on-copy -r%d:HEAD %s' % (
                        cur_branch_creat_rev, self.source_branch_url))):
            cx_rev = cx.revision()
            if cx_rev < cur_branch_creat_rev:
                break

            if cx_rev in self.ignored_commits:
                continue

            if cx_rev in self.already_merged_commits:
                continue

            self.available_commits.append(cx)

    def print_available_commits(self, show_files):
        mark_line = {
            self.STATE_SHOW_AVAIL_COMMITS: lambda x: '',
            self.STATE_MARK_FOR_IGNORE: lambda x: '* ' if x in self.marked_commits else '  ',
            self.STATE_MARK_FOR_COMMIT: lambda x: '* ' if x in self.marked_commits else '  '
        }
        # TODO gérer la pagination pour le cas où l y a trop de commits en attente
        if len(self.available_commits) > 0:
            n, page = 1, 1
            for chg in self.available_commits:
                log_revision = chg.revision()

                # transforme les messages multilignes en une seule ligne
                msg = '|'.join(chg.msg().split('\n'))
                print((Fore.RED + mark_line[self.loop_state](n) + Fore.RESET +
                       Fore.YELLOW + u"{0:d}. " +
                       Fore.GREEN + u"R{1:d} {2:s} " +
                       Fore.MAGENTA + u"{3:s} " +
                       Fore.RESET + u"{4:s}").format(n, log_revision, chg.date(), chg.author(), msg))
                n += 1
                if show_files:
                    for path in chg.paths():
                        print((Fore.BLUE + u"    {0:s} {1:s}" + Fore.RESET).format(path.action(), path.pathid()))
        else:
            print(Fore.GREEN + u"Il n'y a pas de nouveaux commits" + Fore.RESET)

    def print_menu(self):
        if self.local_copy_dirty:
            print(Fore.RED + 'Copie locale modifiée' + Fore.RESET)
        state_names = {
            self.STATE_SHOW_AVAIL_COMMITS: lambda: '',
            self.STATE_MARK_FOR_IGNORE: lambda: Fore.RED + u"Lignes marquées pour être IGNOREES",
            self.STATE_MARK_FOR_COMMIT: lambda: Fore.RED + u"Lignes marquées pour être FUSIONNEES"
        }
        print(state_names[self.loop_state]())
        state_menus = {
            self.STATE_SHOW_AVAIL_COMMITS: lambda:
            ((Fore.YELLOW + u"D" + Fore.RESET + u" montre/cache les détail des fichiers | " +
              Fore.YELLOW + u"F" + Fore.RESET + u" Marquer pour fusion... | " +
              Fore.YELLOW + u"I" + Fore.RESET + u" Marquer pour ignorer... | ")
             if len(self.available_commits) > 0 else "") +
            Fore.YELLOW + u"Q" + Fore.RESET + u" Quitter",
            self.STATE_MARK_FOR_IGNORE: lambda:
            Fore.YELLOW + u"V" + Fore.RESET + u" Valider le choix" +
            Fore.YELLOW + u"I" + Fore.RESET + u" Marquer d'autres lignes..." +
            Fore.YELLOW + u"D" + Fore.RESET + u" montre/cache les détail des fichiers | " +
            Fore.YELLOW + u"Q" + Fore.RESET + u" Quitter",
            self.STATE_MARK_FOR_COMMIT: lambda:
            Fore.YELLOW + u"V" + Fore.RESET + u" Valider le choix | " +
            Fore.YELLOW + u"F" + Fore.RESET + u" Marquer d'autres lignes... | " +
            Fore.YELLOW + u"D" + Fore.RESET + u" montre/cache les détail des fichiers | " +
            Fore.YELLOW + u"Q" + Fore.RESET + u" Quitter",
        }
        print(state_menus[self.loop_state]())

    def main(self):
        global opts
        try:
            # la commande doit être exécutée dans une copie locale SVN, à la racine
            self.check_local_copy()

            # la copie locale ne doit avoir aucune modification non-commitée (enfin, en principe)
            self.check_clean_local_copy()

            # mise à jour de la copie locale
            self.update_local_copy()

            # début de la boucle de traitement principale
            show_files = False
            while 1:
                if self.loop_state == self.STATE_SHOW_AVAIL_COMMITS \
                        or self.loop_state == self.STATE_NO_MORE_COMMITS:
                    self.read_available_commits()

                self.print_available_commits(show_files)

                self.print_menu()
                choix = input().capitalize()
                if choix == 'Q':
                    print("Quitter...")
                    break

                if choix == 'D':
                    show_files = not show_files
                    continue

                state_menu_fn = {
                    self.STATE_SHOW_AVAIL_COMMITS: {
                        'F': self.enter_mark_merge,
                        'I': self.enter_mark_ignore
                    },
                    self.STATE_MARK_FOR_IGNORE: {
                        'V': self.do_mark_ignore,
                        'I': self.enter_mark_ignore
                    },
                    self.STATE_MARK_FOR_COMMIT: {
                        'V': self.do_merge,
                        'F': self.enter_mark_merge
                    }
                }

                # ceci appelle la méthode désignée pour l'opération courante
                if choix in state_menu_fn[self.loop_state].keys():
                    program_stop = state_menu_fn[self.loop_state][choix]()
                    if program_stop:
                        break
                else:
                    print(u"Choix %s inconnu!" % choix)

            if self.local_copy_dirty:
                print(Fore.GREEN + u"Les opérations ont été consignées dans le fichier %s" % COMMIT_MESSAGE_FILE_NAME)
                print(u"N'oublier pas de le prendre en compte ainsi :" + Fore.RESET)
                print(Fore.YELLOW + u"svn commit -F %s" % COMMIT_MESSAGE_FILE_NAME + Fore.RESET)
            print('FIN.')

        except KeyboardInterrupt:
            print(u"Arrêt demandé par l'utilisateur")
            sys.exit(1)

    def read_ignored_commits(self):
        svnout = Svn.launch("propget --strict " + self.SVN_PROP_IGNORED_COMMITS)
        if len(svnout) > 0:
            self.ignored_commits = [int(x) for x in svnout.split(',')]
        else:
            self.ignored_commits = []

    def input_commits(self, desired_state):
        print(u"Entrer les numéros des commits (p.ex. 1,3-5,8) : ")
        choix_commits_in = input()
        if len(choix_commits_in) == 0:
            print(u"Opération abandonnée")
        else:
            self.loop_state = desired_state
            choix_commits1 = choix_commits_in.split(',')
            for cx in choix_commits1:
                if cx.find('-') > 0:
                    r = cx.split('-')
                    for i in list(range(int(r[0]), int(r[1]) + 1)):
                        self.marked_commits.append(int(i))
                else:
                    self.marked_commits.append(int(cx))

    def enter_mark_ignore(self):
        self.input_commits(self.STATE_MARK_FOR_IGNORE)
        return False  # e.g. the program should continue

    def do_mark_ignore(self):
        """
        Les commits ignorés sont déposés dans une propriété de la copie locale
        """
        # utilisation d'une copie locale de ignored_commits
        # la variable globale sera relue dans la boucle principale
        ignored_commits = self.ignored_commits + \
                          [str(self.available_commits[i - 1].revision()) for i in self.marked_commits]
        ignore_prop = ",".join([str(x) for x in ignored_commits])
        if opts["verbose"] >= 2:
            print(ignore_prop)

        Svn.launch("propset %s %s ." % (self.SVN_PROP_IGNORED_COMMITS, ignore_prop))

        self.update_commit_message("commits marqués comme ignorés : %s\n" %
                                   ','.join([str(x) for x in self.ignored_commits]))
        self.local_copy_dirty = True
        # NOTE ceci n'est pas encore commité

        # à la fin, réinitialization et relecture des commits
        self.loop_state = self.STATE_SHOW_AVAIL_COMMITS
        self.marked_commits.clear()
        return False  # e.g. the program should continue

    def enter_mark_merge(self):
        self.input_commits(self.STATE_MARK_FOR_COMMIT)
        return False  # e.g. the program should continue

    def update_commit_message(self, msg):
        self.commit_message += msg
        try:
            f = open(COMMIT_MESSAGE_FILE_NAME, 'w')
            f.write(msg)
            f.close()
        except Exception as err:
            print(str(err))

    def do_merge(self):
        """
        Les commits sélectionnés sont fusionnés dans la copie locale
        """
        commits_done = []
        msgs = []
        conflict_re = re.compile("^\s*C\s+.*")
        conflict = False
        for i in self.marked_commits:
            mc = self.available_commits[i - 1]
            try:
                r = mc.revision()
                print("Fusion de la révision %s..." % r)
                merge_out = Svn.launch("merge -c%d --depth=infinity %s" % (r, self.source_branch_url))
                msgs.append((mc.revision(), mc.msg()))
                commits_done.append(i)
                self.local_copy_dirty = True

                # recherche des indications de conflits dans la sortie de svn
                conflict = len([l for l in merge_out.split('\n') for m in (conflict_re.match(l),) if m]) > 0
                if conflict:
                    print(Fore.RED + u'Il y a des conflits:' + Fore.RESET)
                    print(merge_out)
                    break
            except CalledProcessError as err:
                print("ERREUR %s" % err.output)
                print("L'opération de fusion a été interrompue.")
                break
        if len(msgs) > 0:
            msg = "Merged revision(s) %s from %s:\n" % (', '.join([str(x[0]) for x in msgs]), self.source_branch)
            msg += "........\n".join([x[1] for x in msgs])
            self.update_commit_message(msg)

        if conflict:
            return True  # ask for program termination

        if self.local_copy_dirty:
            print("Opération terminée. La copie locale a été affectée.")
        else:
            print("Opération terminée. La copie locale n'a pas été affectée.")

        self.loop_state = self.STATE_SHOW_AVAIL_COMMITS
        self.marked_commits.clear()
        return False  # e.g. the program should continue


if __name__ == "__main__":
    global opts
    init()  # init de colorama

    parser = argparse.ArgumentParser()
    parser.add_argument('sourcepath', metavar=OPT_SOURCEPATH,
                        help=u"URL de la branche source. Si vous mettez ? alors le programme va afficher la liste des branches déjà connues et vous permettra de choisir la branche désirée à partir de cette liste.")
    parser.add_argument('--verbose', dest='verbose', type=int, default=0,
                        help=u"Le niveau de verbosité de l'exécution")
    # TODO ajouter un argument pour afficher les commits disponibles en ordre inverse
    # TODO internationnaliser les messages ?
    opts = vars(parser.parse_args())

    svn_merge = SvnMerge()
    svn_merge.main()
