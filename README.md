Hello, there!

This project has the objective of creating a spreadsheet with solubility data from electrolytic ternary mixtures.
If you just fetched this project's data from .github, its imperative to follow these instructions:

#1 Don't change any fetched folder or file name nor move from its original locations;
#2 Make a copy of "settings_template.json" file and rename it's copy as "settings.json";
#3 Open "settings.json" you just created, you will see some arguments with "", you will need to fill these blank spaces;
#4 In order to add your local input path (in other words, where the input spreadhsheet, "tabela_de_sais_linke.xlsx", is), open "data" folder, you will now see two folders, right click "input" folder and select "copy as path" option. After this, go to "settings.json" you just created and paste it (Ctrl + V), filling the "" from "input_path";
#5 Now you need to configure the output settings (both path and file name);
#6 In order to add your local output path, just follow step #4 by selecting "output" instead of "input" folder and fill the "" from "output_path" at settings.json (note that a custom output folder may be sellected at your desire by simply choosing a valid folder from your local machine);
#7 Finally, just choose a custom name at your liking and fill "" from "output_file".

Once you are done with these steps, you are good to run main.py. A spreadsheet with "output_file" name will be created at "output_file" location.