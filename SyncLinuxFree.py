from math import ceil
import os, pwd, re, hashlib
from shutil import which
from struct import calcsize
from click import command
import pandas as p
from subprocess import Popen, PIPE
import asyncio


class Display():
    def __init__(self) -> None:
        self.title = "SyncLinuxFree"
        self.borders = {
            "title": {
                "corners": "#",
                "h_edge": "=",
                "v_edge": "|"
            },
            "corners": "#"
        } 
        
        self.data = Data()
        self.prompt = Prompt({})
        self.syncer = Syncer()

        self.synchro_input_dirs = None
        self.synchro_target_dir = None
        self.curr_syncer_data_values = None
        
        self.refresh_display()

        self.history = "Initialisation"
        self.help_list = []

        self.display_type = "data"
        self.display_name = ""
        self.new_data_info = None

        self.next_displayed_data = 1
        self.text_next_displayed_data = 1

        self.command = None
        self.executes = True
        self.can_validate = True

    def display(self):
        self.clear()
        self.refresh_display()
        
        self.print_title(self.term_size.columns)
        self.display_selector()

        nb_printed_lines = self.last_displayed_data - self.first_displayed_data - 1
        if nb_printed_lines < self.max_displayed_rows:
            print("\n" * (self.max_displayed_rows - nb_printed_lines - 2))
        
        
        override_validation = True if self.display_name == "syncer overview" else False

        if not self.syncer.ongoing:
            print("_" * self.term_size.columns)
            print(f"INFOS: {self.history}")
            print("_" * self.term_size.columns)
        
            self.command = self.prompt.render_prompt(override_validation)

    def print_title(self, term_width):
        title_spacing = " " * ((term_width - len(self.title)) // 2)
        title_frame = title_spacing + self.borders["title"]["corners"] + self.borders["title"]["h_edge"] * (2 + len(self.title)) + self.borders["title"]["corners"]
        print(title_frame)
        print(title_spacing + self.borders["title"]["v_edge"] + f" {self.title} " + self.borders["title"]["v_edge"])
        print(title_frame)
        print("\t")
    
    def generate_help(self):
        if self.term_size[0] < 10:
            self.help_list = ["Fenêtre trop petite, aggrandissez la puis entrez 'rafraichir'."]
            return
        
        self.help_list = [f"Bienvenue dans l'aide de {self.title}.",
            "Pour retourner au menu précédent, entrez 'retour'.",
            "Pour changer de page utiliser 'precedent' ou 'suivant'",
            "",
            f"Vous étiez dans le menu {self.display_name}"]

        if self.display_name == "dossiers à synchroniser":
            self.help_list.extend(["Depuis ce menu vous devez choisir les dossiers à synchroniser.",
                "Pour cela, entrez une liste de numéro de lignes afin de modifier leur statut.",
                "Ceux-ci doivent être séparés par des espaces pour être correctement pris en compte.",
                "Vous pouvez également utiliser la commande 'tous' pour faire basculer le status de tous les dossier vers leurs opposés.",
                "Enfin il est possible d'entre une plage de données de la manière suivante : 'n-m'.",
                "Cela peut être combiné avec les autres commandes, excepté 'tous'."])
        elif self.display_name == "périphérique cible":
            self.help_list.extend(["Depuis ce menu il vous faut choisir le périphérique destination.",
            "Entrez simplement le numéro de ligne du périphérique souhaité.",
            "Une fois la commande exécutée, validez pour passer au menu suivant."])
        elif self.display_name == "dossier cible":
            self.help_list.extend(["Depuis ce menu il vous faut choisir le dossier destination.",
            "Il vous est proposé une liste de dossier trouvés sur le périphérique précédement choisit.",
            "Si vous souhaitez créer une nouveau dossier, faites le depuis votre explorateur de fichier,",
            "puis entrez 'rafraichir'",
            "Entrez simplement le numéro de ligne du dossier cible souhaité.",
            "Une fois la commande exécutée, validez pour passer au menu suivant."])

        self.help_list.extend(["",
            "Ci-après la liste des commandes disponnibles:"])

        for command in self.prompt.action_list:
            self.help_list.append(f"\t- {command} : {self.prompt.action_list[command]}")

    def text_page_selector(self, text):
        lines_range = range(len(text) + 1)
        split_text = [lines_range[i:i+self.max_displayed_rows] for i in range(0, len(lines_range), self.max_displayed_rows)]

        if not self.text_next_displayed_data in lines_range:
            self.history = "Plus de données de ce côté ci."
            if self.text_next_displayed_data < 0:
                self.text_next_displayed_data += 1
            else:
                self.text_next_displayed_data -= 1

        for sub_list in split_text:
            if self.text_next_displayed_data in sub_list:
                page_curr = split_text.index(sub_list) + 1
                last_value = sub_list[-1]
                first_value = sub_list[0]
                displayed_text = text[first_value:last_value + 1]
                break

        return displayed_text, page_curr, first_value, last_value
        
    def print_text(self):

        if self.display_type == "help":
            self.generate_help()
            text = self.help_list

        else:
            text = self.syncer.syncer_output_data

        sub_text, page_curr, first_value, last_value = self.text_page_selector(text)
       
        for row in sub_text:
            print(row, end="\n")

        page_tot = ceil(len(text) / self.max_displayed_rows)
        print(f"\nPAGE: {page_curr}/{page_tot}")

        return [ first_value, last_value ]

    def refresh_display(self):
        self.term_size = os.get_terminal_size()
        self.max_displayed_rows = self.term_size.lines - 14

    def clear(self):
        os.system("clear")

    def display_selector(self):
        if self.display_type == "data":
            self.first_displayed_data, self.last_displayed_data = self.data.print_data(self.max_displayed_rows, self.next_displayed_data)
            self.display_name = self.data.name
        elif self.display_type == "help":
            self.text_first_displayed_data, self.text_last_displayed_data = self.print_text()
        elif self.display_type == "syncer":
            if self.syncer.syncer_output_type == "text":
                self.text_last_displayed_data = len(self.syncer.syncer_output_data)
                self.print_text()
            else:
                self.syncer_handler()

    def syncer_handler(self):
        if self.curr_syncer_data_values is None:
            self.curr_syncer_data_values = self.syncer.syncer_output_data["dir_status"]
            self.data.change_data("syncer overview", self.curr_syncer_data_values)
            self.history = "Analyse achevée, veuillez modifier ou valider le statut de synchronisation des fichiers."
            self.first_displayed_data, self.last_displayed_data = self.data.print_data(self.max_displayed_rows, self.next_displayed_data)
            self.display_name = self.data.name
        else:
            self.first_displayed_data, self.last_displayed_data = self.data.print_data(self.max_displayed_rows, self.next_displayed_data)
            self.display_name = self.data.name

    def base_commands_handler(self):
        if self.command is None:
            return False

        if not self.command in self.prompt.action_list.keys():
            self.history = "Commande inconnue. Utiliser la commande 'aide' pour plus d'informations."
            return False

        if self.command == "aide":
            self.display_type = "help"
            self.help_next_displayed_data = 1

        elif self.command == "retour":
            if self.display_type == "help":
                self.display_type = "data"
                self.help_next_displayed_data = 1
                self.history = "Fermeture du menu d'aide."
            elif self.display_name == "syncer subdata":
                self.data.df = self.data.all_data["syncer subdata"]
                self.data.change_data("syncer overview", self.syncer.syncer_output_data["dir_status"])
                self.history = f"Annulation des changements."
            else:
                self.history = "La commande 'retour' n'est pas disponible ici."

        elif self.command == "suivant":
            if self.display_type == "help":
                self.help_next_displayed_data = self.help_last_displayed_data + 1 
            else:
                self.next_displayed_data = self.last_displayed_data + 1 
            self.history = "Affichage page suivante."

        elif self.command == "precedent":
            if self.display_type == "help":
                self.help_next_displayed_data = self.help_first_displayed_data - 1 
            else:
                self.next_displayed_data = self.first_displayed_data - 1
            self.history = "Affichage page précédente."

        elif self.command == "debut":
            if self.display_type == "help":
                self.help_next_displayed_data = 1 
            else:
                self.next_displayed_data = 1 
            self.history = "Affichage de la première page."

        elif self.command == "fin":
            if self.display_type == "help":
                self.help_next_displayed_data = len(self.help_list) 
            else:
                self.next_displayed_data = self.data.df.shape[0] 
            self.history = "Affichage de la dernière page."


        elif self.command == "quitter":
            self.executes = False

        elif self.command == "rafraichir":
            self.history = "Rafraichissement de la page."
            self.data.change_data(self.display_name, self.new_data_info)

        elif self.command == "recommencer":
            self.history = f"Réinitialisation du programme."
            self.data = Data()
            self.prompt = Prompt({})
            self.display_type = "data"

        elif self.command == "sauvegarder":
            if self.display_name == "syncer overview":
                asyncio.run(self.syncer.sync())
            else:
                self.history = "Impossible de lancer la sauvegarde d'ici."

        elif self.command == "valider":
            if not self.can_validate:
                self.history = "Impossible de valider, commande non conforme."
                return False

            if self.display_name == "dossiers à synchroniser":
                self.synchro_input_dirs = list(self.data.df[self.data.df["Sera synchronisé"] == True].iloc[:, 0])
                self.synchro_input_dirs = [ self.data.home_dir + '/' + item for item in self.synchro_input_dirs ]
                self.data.change_data("périphérique cible")
                self.history = "Dossiers validés, veuillez choisir le périphérique cible."

            if self.display_name == "périphérique cible":
                self.data.change_data("dossier cible", self.new_data_info)
                self.history = f"Périphérique validé ({self.target_device}), veuillez choisir le dossier cible."

            if self.display_name == "dossier cible":
                self.synchro_target_dir = f"{self.target_device}/{self.target_folder}"
                self.history = f"Chemin de sauvegarde défini ({self.synchro_target_dir})"
                self.display_type = "syncer"
                self.syncer = Syncer(self.synchro_input_dirs, self.synchro_target_dir)
                self.prompt.action_list["sauvegarder"] = "Lancer la sauvegarde miroir."

            if self.display_name == "syncer overview":
                self.data.change_data("syncer subdata", self.syncer.syncer_output_data[self.new_data_info])
                self.history = f"Vous entrez dans le détail de {self.new_data_info}."

            if self.display_name == "syncer subdata":
                self.syncer.syncer_output_data[self.new_data_info] = self.data.df.copy()
                self.syncer.update_stats()
                self.data.change_data("syncer overview", self.syncer.syncer_output_data["dir_status"])
                self.history = f"Changements validés, veuillez choisir un autre dossier ou 'sauvegarder' pour lancer la sauvegarde miroir."
            
            self.display_name = self.data.name
            self.can_validate = False

        return True
            
    def specific_commands_handler(self):
        if self.command is None:
            return False

        self.can_validate = False

        if self.display_name == "dossiers à synchroniser" or self.display_name == "syncer subdata":
            if self.command == "tous":
                rows = range(1, self.data.df.shape[0] + 1) 
            else:
                rows = self.command.split()
                for row in rows:
                    row = str(row)
                    if re.match('[0-9]+-[0-9]+', row):
                        curr_index = rows.index(row)
                        rows.pop(curr_index)
                        row = row.split('-')
                        rows[curr_index:curr_index] = range(int(row[0]), int(row[1]) + 1)
                for i in range(len(rows)):
                    try:
                        rows[i] = int(rows[i])
                    except:
                        #self.history = "La commande semble ne pas contenir uniquement des nombres entiers."
                        return
            
            wrong_rows = self.data.switch_status(rows)
            ok_rows = [ i for i in rows if not i in wrong_rows ]
            if len(ok_rows) != 0:
                self.history = f"Mis à jour: {ok_rows}."
            if len(wrong_rows) != 0:
                self.history += f" Non mis à jour {wrong_rows}."
            self.history += "Validez pour choisir le dossier destination."
            self.can_validate = True

        elif self.display_name == "périphérique cible" or self.display_name == "dossier cible" or self.display_name == "syncer overview":
            try:
                self.command = int(self.command)
            except:
                #self.history = "La commande semble ne pas contenir un nombre entier."
                return
            if self.command in range(self.data.df.shape[0] + 1):
                target_column = "Emplacement" if self.display_name == "périphérique cible" else "Dossiers"
                target_column = "Dossiers sources" if self.display_name == "syncer overview" else target_column

                self.new_data_info = self.data.df.at[self.command, target_column]
                if self.display_name == "syncer overview":
                    self.new_data_info = self.new_data_info.split("/")[-1]

                next_display = "choisir le dossier destination" if self.display_name == "périphérique cible" else "commencer le comparatif source/destination"
                next_display = f"choisir les fichiers à synchroniser dans {self.new_data_info}" if self.display_name == "syncer overview" else next_display

                self.history = f"Vous avez sélectionné {self.new_data_info}. Validez pour {next_display}."
                if self.display_name == "périphérique cible":
                    self.target_device = self.new_data_info
                else:
                    self.target_folder = self.new_data_info

                self.can_validate = True


class Data():
    def __init__(self) -> None:
        self.home_dir = os.path.expanduser('~')
        dir_list = next(os.walk(self.home_dir))[1]
        self.switch_colname = "Sera synchronisé"
        self.df = p.DataFrame(
            {"Dossiers" : dir_list,
            self.switch_colname : [True] * len(dir_list)},
            index = range(1,len(dir_list)+1))
        
        self.all_data = {
            "dossiers à synchroniser"   : self.df,
            "périphérique cible"        : None,
            "dossier cible"             : None,
            "syncer overview"           : None,
            "syncer subdata"            : None}

        self.previous_data  = None
        self.name = "dossiers à synchroniser"

    def print_data(self, max, next_value = 1):
        if self.df.shape[0] < max :
            sub_df = self.df
            page_curr = 1
            first_value = 1
            last_value = self.df.shape[0]
        else: 
            sub_df, page_curr, first_value, last_value = self.sub_table_generator(max, next_value)
        
        print(sub_df.to_markdown())

        page_tot = ceil(self.df.shape[0] / max)
        print(f"\nPAGE: {page_curr}/{page_tot}")

        return [first_value, last_value]
    
    def sub_table_generator(self, max, next_value):
        lines_range = range(self.df.shape[0])
        split_df = [lines_range[i:i+max] for i in range(0, len(lines_range), max)]        
        
        if not next_value in lines_range:
            if next_value < 0:
                next_value += 1
            else:
                next_value -= 1

        for sub_list in split_df:
            if next_value in sub_list:
                page_curr = split_df.index(sub_list) + 1
                last_value = sub_list[-1]
                first_value = sub_list[0]

                displayed_df = self.df.iloc[first_value:last_value + 1]
                break
        return displayed_df, page_curr, first_value, last_value

    def switch_status(self, rows):
        wrong_rows = []
        for row in rows:
            if row in range(1, self.df.shape[0] + 1):
                self.change_value(row, self.switch_colname, not bool(self.get_value(row, self.switch_colname)))
            else:
                wrong_rows.append(row)
        return wrong_rows

    def change_value(self, row, column, value):
        self.df.at[row, column] = value
    
    def get_value(self, row, column):
        return self.df.at[row, column]

    def change_data(self, which_data, new_info = None):
        self.previous_data = self.name
        self.name = which_data

        if which_data == "périphérique cible":
            cmd = "df -Th | sed 's/\s\+/,/g'"
            with Popen(cmd, shell = True, stdout = PIPE) as process:
                df = p.read_csv(process.stdout)
                
            df = df[['Size', 'Use%', 'Mounted']].rename(columns = {
                'Size': 'Taille', 
                'Use%': '% Utilisé', 
                'Mounted': 'Emplacement'})
            df = df[df['Emplacement'].str.match('.*media.*')].reset_index()[['Taille', '% Utilisé', 'Emplacement']]
            df.index += 1 
            
        if which_data == "dossier cible":
            dir_list = next(os.walk(new_info))[1]
            df = p.DataFrame(
                {"Dossiers" : dir_list},
                index = range(1,len(dir_list)+1))
            
        if which_data == "syncer overview":
            df = new_info.copy()
            
        if which_data == "syncer subdata":
            df = new_info.copy()
            
        # Backup old df & replace by new one
        self.all_data[self.previous_data] = self.df
        self.df = df
        self.all_data[self.name] = self.df
        

class Prompt():
    def __init__(self, action_list) -> None:
        self.action_list = {"aide": "Mène à ce menu contextuel.", 
            "retour": "Permet de retourner à l'écran précédent.",
            "quitter": "Quitte le proggramme.", 
            "rafraichir": "Permet de rafraichir l'affichage et de le redimensionner à votre fenêtre.", 
            "recommencer": "Réinitialise le programme.", 
            "suivant": "Affiche la page suivante", 
            "precedent": "Affiche la page précédente.",
            "debut": "Affiche la première page.",
            "fin": "Affiche la dernière page.",
            "valider": "Passer au menu suivant."}
        for elem in action_list:
            self.action_list[elem] += action_list[elem]
        username = pwd.getpwuid(os.getuid())[0]
        self.prompt = f"{username} > "
        self.validation_prompt = False
    
    def render_prompt(self, override_validation = True):
        command = input(self.prompt)
        
        if command == "valider" and override_validation:
            self.validation_prompt = False
        elif command in ["valider", "recommencer", "quitter", "sauvegarder"]:
            self.validation_prompt = True
        else:
            self.validation_prompt = False

        if self.validation_prompt:
            print("Valider (o/n) >", end=" ")
            validate = str(input()).lower()
            LINE_UP = '\033[1A'
            LINE_CLEAR = '\x1b[2K'
            while not validate in ["o", "n"]:
                print(LINE_UP, end=LINE_CLEAR)
                print("Valider (o/n) >", end=" ")
                validate = str(input()).lower()
                
            if validate == "n":
                command = "ABORT"

        return command


class Syncer():
    def __init__(self, source_dirs = None, target_dir = None) -> None:
        self.source_dirs = source_dirs
        self.target_dir = target_dir

        self.is_backed_list = []

        self.syncer_output_type = "text"
        self.syncer_output_data = ["Nous sommes en train de déterminer quelles données nous devons synchroniser.",
            "Veuillez patienter..."]

        self.data_gathered = False

        self.ongoing = False if source_dirs is None else True 
    
    def gather_data(self):

        self.syncer_output_data = {}
        list_backed_dirs =  next(os.walk(self.target_dir))[1]
        
        
        for a_dir in self.source_dirs:
            curr_dir = a_dir.split('/')[-1]
            self.is_backed_list.append(f"{self.target_dir}/{curr_dir}") if curr_dir in list_backed_dirs else self.is_backed_list.append(None)
            self.syncer_output_data[curr_dir] = self.harvest_data(a_dir)

        dir_list_df = self.calc_stats()
        
        self.syncer_output_type = "data"
        self.syncer_output_data["dir_status"] = dir_list_df

        self.data_gathered = True
        self.ongoing = False

    def harvest_data(self, folder):
        curr_folder = folder.split('/')[-1]
        target_folder = f"{self.target_dir}/{curr_folder}"
        # Récupératon de la liste de fichiers
        source_data = [ [root, files] for (root,dirs,files) in os.walk(folder, topdown=True)]
        dest_data = [ [root, files] for (root,dirs,files) in os.walk(target_folder, topdown=True)]
        # Permet de créer une liste contenant des couples [path, fichier]
        for data_name in ["source_data", "dest_data"]:
            if data_name == "source_data":
                data = source_data
            else:
                data = dest_data

            new_data = []
            for row in data:
                try:
                    if isinstance(row[1], list):
                        files = [[row[0], file ] for file in row[1] if file]
                    else:
                        files = row
                    if files:
                        for file in files:
                            new_data.append(file)
                except:
                    pass
        
            if data_name == "source_data":
                source_data = new_data[:]
            else:
                dest_data = new_data[:]

        # Comparaison des sources et destinations
        status_source = []
        match_dest_id = []
        status_dest = []
        # On analyse d'abord la source pour voir si ses fichiers sont présents, absents, modifiés, déplacés, ...  
        for source_file in source_data:
            found_one = False

            for dest_file in dest_data:
                if source_file[1] == dest_file[1]:
                    found_one = True
                    
                    full_path_source =f"{source_file[0]}/{source_file[1]}"
                    rel_path_source = re.sub(folder + "/", "", full_path_source)
                    full_path_dest = f"{dest_file[0]}/{dest_file[1]}"
                    rel_path_dest = re.sub(target_folder + "/", "", full_path_dest)

                    if rel_path_source == rel_path_dest:
                        if self.hash_file(full_path_source) == self.hash_file(full_path_dest):
                            status_source.append("IDENTIQUE")
                        else:
                            status_source.append("MODIFIE")
                    else:
                        status_source.append("DEPLACE")
                    
                    match_dest_id.append(dest_data.index(dest_file))
                    break
            if not found_one:
                status_source.append("AJOUTE")
                match_dest_id.append(None)
        # ... On formate la liste de fichier destination avec les indexes définis ci-dessus, ...
        processed_dest_data = []
        for match in match_dest_id:
            if match is None:
                processed_dest_data.append(None)
            else:
                processed_dest_data.append(f"{dest_data[match][0]}/{dest_data[match][1]}")
        # ... Et on crée le tableau de données !       
        output_data = p.DataFrame({
            "Statut":           status_source,
            "Fichier source" :  [ f"{data[0]}/{data[1]}" for data in source_data ],
            "Fichier dest" :    processed_dest_data},
            index= range(1, len(processed_dest_data) + 1))

        # On analyse ensuite la destination pour voir si ces fichiers ont été supprimés, afin de les rajouter au tableau ci dessus.
        for dest_file in dest_data:
            found_one = False
            for source_file in source_data:
                if source_file[1] == dest_file[1]:
                    found_one = True
                    status_dest.append("OK")
                    break
            if not found_one:
                    status_dest.append("SUPPRIME")
        # On crée une liste de booléens pour trouver les éléments qui ne sont pas encore dans le tableau de sortie ...
        boolify = lambda a,b : True if a == b else False
        boolified_list = [ boolify(elem, "SUPPRIME") for elem in status_dest]
        new_status_dest = [elem for elem in status_dest if boolified_list[status_dest.index(elem)]]
        new_file_list_dest = [elem for elem in dest_data if boolified_list[dest_data.index(elem)]]
        # ... Afin de les ajouter à un tableau qui sera concaténé avec le précédent.
        add_data = p.DataFrame({
            "Statut": new_status_dest,
            "Fichier source" :  [None] * len(new_status_dest),
            "Fichier dest" :    [ f"{data[0]}/{data[1]}" for data in new_file_list_dest ]},
            index = range(1, len(new_status_dest) + 1))

        output = p.concat([output_data, add_data]).reset_index()[['Statut', 'Fichier source', 'Fichier dest']]
        output["Sera synchronisé"] = [True] * output.shape[0]
        output.index += 1
        return output
    
    def calc_stats(self):
        stats = {}

        for table in self.syncer_output_data:
            if table == "dir_status":
                continue

            curr_table = self.syncer_output_data[table]
            stats[table] = curr_table["Statut"].where(curr_table["Sera synchronisé"] != False).value_counts().to_frame() 
            for cols in ["IDENTIQUE", "AJOUTE", "MODIFIE", "DEPLACE", "SUPPRIME"]:
                if not cols in stats[table].index:
                    stats[table] = p.concat([stats[table], p.DataFrame([None],index=[cols],columns=stats[table].columns)])

        dir_list_df = p.DataFrame(
            {"Dossiers sources" : self.source_dirs,
            "Dossiers cibles" : self.is_backed_list,
            "# id.":    [stats[table].at["IDENTIQUE", "Statut"] for table in stats ],
            "# ajout":  [stats[table].at["AJOUTE", "Statut"]    for table in stats ],
            "# mod.":   [stats[table].at["MODIFIE", "Statut"]   for table in stats ],
            "# depl.":  [stats[table].at["DEPLACE", "Statut"]   for table in stats ],
            "# supr.":  [stats[table].at["SUPPRIME", "Statut"]  for table in stats ]},
            index = range(1, len(self.source_dirs) + 1) 
        )

        return dir_list_df

    def update_stats(self):
        self.syncer_output_data["dir_status"] = self.calc_stats()

    async def sync(self):
        self.syncer_output_type = "text"
        self.ongoing = True

        self.syncer_output_data = ["lol"]

        await asyncio.sleep(30)

        self.syncer_output_data = ["LOL"]
        self.ongoing = False

    def hash_file(self, filename):
        """"This function returns the SHA-1 hash
        of the file passed into it"""

        # make a hash object
        h = hashlib.sha1()

        # open file for reading in binary mode
        with open(filename,'rb') as file:

            # loop till the end of the file
            chunk = 0
            while chunk != b'':
                # read only 1024 bytes at a time
                chunk = file.read(1024)
                h.update(chunk)

        # return the hex representation of digest
        return h.hexdigest()      


os.system('rm -rf /media/e/backup/A_test/*')
os.system('cp ~/B_test/* /media/e/backup/A_test/')
screen = Display()
is_cmd_ok = False
while screen.executes:
    screen.display()

    if screen.syncer.ongoing:
        if not screen.syncer.data_gathered:
            screen.syncer.gather_data()
            screen.syncer.ongoing = False
            screen.syncer.syncer_output_type = "data"

    else:
        is_cmd_ok = screen.base_commands_handler()
        if not is_cmd_ok:
            screen.specific_commands_handler()
    
    #input("temporisation")

os.system('clear')
print("Fin d'exécution du programme de sauvegarde de fichiers.")
