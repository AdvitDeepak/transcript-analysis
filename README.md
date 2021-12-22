# Transcript Analysis - Graph + NLP

This program extracts insights from Zoom Meeting Transcripts (`.vtt`) using TigerGraph and NLTK.

In order to run this program, modify the `auth.ini` file with your proper graph solution credentials
and file paths. Then, simply run `main.py`. A sample transcript has already been provided.

As of now, this program performs the following tasks:

1. Convert `.vtt` into compact version (stored in `\b_cmt_transcripts`)

2. Graph analysis of compact transcript (using TigerGraph)
   - Analyze relationships between speakers
     - Asked the most/least question
     - Pair w/ the most back-and-forth
   - (TODO): Linking topics in semantic graph
   - (TODO): Named-Entity Recognition

3. NLP analysis of compact transcript (using nltk)
   - Most common words (shown as wordcloud)
   - Number of speakers, names of speakers
   - Who spoke the longest, least, average

 4. Visual output of all determined insights


## Usage

A TigerGraph Cloud Portal account will be required to run this demo. The schema utilized in this graph is fleshed out below:

Vertex: speaker
- (PRIMARY ID) name - STRING

Edge: asked_question
- text - STRING

Edge: answered_question

Kindly find the GraphStudio link here: https://https://transcript-analysis.i.tgcloud.io/

&nbsp; &nbsp;

Here is an example of the graph populated with the sample transcript provided:

![GraphStudio](./Screenshots/graphstudio.png)

## Analysis

Here is a screenshot of the command-line output produced:

![CMD-Output](./Screenshots/cmd_output.png)

Here is a frequency chart of meaningful words generated:

![Freq-Output](./Screenshots/common_words.png)

Here is a word cloud that visualizes common, key terms:  

![Cloud-Output](./Screenshots/word_cloud.png)

More features coming soon! Feel free to suggest and expand! 

## References

* [Zoom Transcript Compacter](https://github.com/lethain/vtt_compactor)
* [TigerGraph documentation](https://docs.tigergraph.com/)
