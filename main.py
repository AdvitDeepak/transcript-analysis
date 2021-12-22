"""
Main file to run. Generates visual output of transcript analysis
Make sure to modify auth.ini with the proper credentials/paths!

Created by: Advit Deepak (GitHub: AdvitDeepak)


1) Convert .vtt into compact version (stored in \b_cmt_transcripts)

2) Graph analysis of compact transcript (using TigerGraph)
   - Analyze relationships between speakers
     o Asked the most/least question
     o Pair w/ the most back-and-forth
   - (TODO): Linking topics in semantic graph
   - (TODO): Named-Entity Recognition

3) NLP analysis of compact transcript (using nltk)
   - Most common words (shown as wordcloud)
   - Number of speakers, names of speakers
   - Who spoke the longest, least, average


 4) Visual output of all determined insights

"""

from os.path import exists
from compact import main_compact
from helpers import *
import configparser


# Step 1 - Convert .vtt into compact version + setup NLTK

config = configparser.ConfigParser()
config.read('auth.ini')

orig_dir = config['paths']['orig_dir']
dest_dir = config['paths']['dest_dir']
source_file = config['paths']['source_file']

parse_file = source_file.split(".vtt")[0]+"_CMT.vtt"
parse_dir = dest_dir + parse_file


if exists(parse_dir):
    print("\n> No new transcript file detected!\n")
else:
    main_compact(orig_dir + source_file)
    print("\n> New transcript file generated!\n")

determiner = PartOfSpeech(config)
print("\n> NLTK classifier set-up and ready-to-go!\n")


# Step 2 - Graph Analysis of compact transcript

gsql_analysis = GraphAnalyzer(config['graph'], parse_dir, determiner)
gsql_analysis.populate_graph()

print("\n> Graph is created and ready to analyze!\n")

# Step 3 - NLP Analysis of compact transcript

nlp_analysis = MiscAnalysis(config, parse_dir)

# Step 4 - Visual Output of all determined insights

nlp_analysis.basicAnalysis()
nlp_analysis.durationsSpoken()

nlp_analysis.generateCloud()
gsql_analysis.run_analytics()
