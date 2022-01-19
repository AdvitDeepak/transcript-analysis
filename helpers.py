"""
Helper functions used by main.py

1) Class PartOfSpeech - used to determine if given phrase is a question
2) Class GraphAnalyzer - used to model the relationship between speakers
3) Class MiscAnalysis - used to create a wordcloud from transcript

Created by: Advit Deepak (GitHub: AdvitDeepak)

"""

import nltk, re, urllib.request
from nltk import word_tokenize
from nltk.probability import FreqDist
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer

import pyTigerGraph as tg
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from statistics import mean


# This class helps determine whether a given phrase is a question

class PartOfSpeech:

    def __init__(self, config):
        nltk.download('nps_chat')
        nltk.download('punkt')

        posts = nltk.corpus.nps_chat.xml_posts()[:10000]
        featuresets = [(self.dialogue_act_features(post.text), post.get('class')) for post in posts]

        size = int(len(featuresets) * 0.1)
        train_set, test_set = featuresets[size:], featuresets[:size]
        self.classifier = nltk.NaiveBayesClassifier.train(train_set)

        self.question_types = ["whQuestion","ynQuestion"]
        self.helping_verbs = ["is","am","can", "are", "do", "does"]

        self.question_pattern = ["do i", "do you", "what", "who", "is it", "why","would you", "how","is there",
                                 "are there", "is it so", "is this true" ,"to know", "is that true", "are we", "am i",
                                 "question is", "tell me more", "can i", "can we", "tell me", "can you explain",
                                 "question","answer", "questions", "answers", "ask"]

        self.config = config


    def dialogue_act_features(self, post):
        features = {}
        for word in nltk.word_tokenize(post):
            features['contains({})'.format(word.lower())] = True
        return features


    def is_ques_using_nltk(self, ques):
        question_type = self.classifier.classify(self.dialogue_act_features(ques))
        return question_type in self.question_types


    def is_question(self, question):
        question = question.lower().strip()
        if not self.is_ques_using_nltk(question):
            is_ques = False
            # check if any of pattern exist in sentence
            for pattern in self.question_pattern:
                is_ques  = pattern in question
                if is_ques:
                    break

            # there could be multiple sentences so divide the sentence
            sentence_arr = question.split(".")
            for sentence in sentence_arr:
                if len(sentence.strip()):
                    # if question ends with ? or start with any helping verb
                    # word_tokenize will strip by default
                    first_word = nltk.word_tokenize(sentence)[0]
                    if sentence.endswith("?") or first_word in self.helping_verbs:
                        is_ques = True
                        break
            return is_ques
        else:
            return True

# This classes uses TigerGraph to analyze the relationship between speakers

class GraphAnalyzer:

    def __init__(self, config, path, determiner):
        TG_HOST = "https://" + config['subdomain'] + ".i.tgcloud.io" # GraphStudio link

        print("Attempting to establish connection with graph solution...")

        self.conn = tg.TigerGraphConnection(host=TG_HOST, username=config['username'], password=config['password'], graphname=config['graphname'])
        self.create_schema()

        self.conn.apiToken = self.conn.getToken(self.conn.createSecret(), setToken=True)
        self.q_n_a = []

        currString = ""; prevSpeaker = ""; currSpeaker = ""

        with open(path, 'r') as vtt:
            for line in vtt:
                match = re.search(r'^\d+[.].*', line)
                if not match: currString += line.strip() + " "; continue

                currSpeaker = line.split(".")[1].strip()
                self.parse_text(currString, prevSpeaker, currSpeaker, determiner)
                currString = ""; prevSpeaker = currSpeaker


    def parse_text(self, curr, prevSpeaker, currSpeaker, determiner):
        sentences = re.split('\.|\?|\!', curr)
        sentences = [sentence.strip() if sentence.strip() != '' else -1 for sentence in sentences]

        asked = False; question = []

        for sentence in sentences:
            if sentence == -1: continue
            if determiner.is_question(sentence):
                asked = True; question.append(sentence); break

        if asked:
            self.q_n_a.append([prevSpeaker, currSpeaker, question])


    def create_schema(self):
        self.conn.gsql(
                  '''
                  USE GLOBAL
                  CREATE VERTEX speaker (PRIMARY_ID name STRING) WITH primary_id_as_attribute="true"
                  CREATE DIRECTED EDGE asked_question (FROM speaker, TO speaker, text STRING) WITH REVERSE_EDGE="reverse_asked_question"
                  CREATE DIRECTED EDGE answered_question (FROM speaker, TO speaker) WITH REVERSE_EDGE="reverse_answered_question"
                  '''
                )
        self.conn.gsql(
                  '''
                  CREATE GRAPH Speakers(speaker, asked_question, answered_question, reverse_asked_question, reverse_answered_question)
                  '''
                 )


    def populate_graph(self):
        print("Populating graph with speakers, questions, and answers...")
        for i in range(len(self.q_n_a)):
            currSpeaker = str(self.q_n_a[i][0])
            nextSpeaker = str(self.q_n_a[i][1])
            question = self.q_n_a[i][2]

            vertices = self.conn.getVertices('speaker')

            if currSpeaker not in vertices:
                self.conn.upsertVertex('speaker', currSpeaker, {})
            if nextSpeaker not in vertices:
                self.conn.upsertVertex('speaker', nextSpeaker, {})

            self.conn.upsertEdge('speaker', currSpeaker, 'asked_question', 'speaker', nextSpeaker, {'text' : str(question)})

            if i + 1 != len(self.q_n_a) and nextSpeaker == self.q_n_a[i+1][0]:
                self.conn.upsertEdge('speaker', nextSpeaker, 'answered_question', 'speaker', currSpeaker, {})


    def run_analytics(self):
        vertices = self.conn.getVertices('speaker')

        maxSpeaker = vertices[0]; maxVal = 0
        minSpeaker = vertices[0]; minVal = 0

        for speaker in vertices:
            questions_asked = self.conn.getEdgeCountFrom('speaker', speaker.get("v_id"), 'asked_question')
            questions_answered = self.conn.getEdgeCountFrom('speaker', speaker.get("v_id"), 'answered_question')
            if (maxVal < questions_asked):
                maxSpeaker = speaker
                maxVal = questions_asked

            if (minVal < questions_answered):
                minSpeaker = speaker
                minVal = questions_answered

        maxSpeaker1 = ""
        maxSpeaker2 = ""
        back_forth = 0

        for speaker1 in vertices:
            for speaker2 in vertices:
                if (speaker1 == speaker2): continue
                try:
                    curr = self.conn.getEdgeCountFrom('speaker', speaker1.get("v_id"), 'asked_question', 'speaker', speaker2.get("v_id"))
                    curr += self.conn.getEdgeCountFrom('speaker', speaker1.get("v_id"), 'answered_question', 'speaker', speaker2.get("v_id"))
                    curr += self.conn.getEdgeCountFrom('speaker', speaker2.get("v_id"), 'answered_question', 'speaker', speaker1.get("v_id"))
                    curr += self.conn.getEdgeCountFrom('speaker', speaker2.get("v_id"), 'answered_question', 'speaker', speaker1.get("v_id"))
                except:
                    curr = 0

                if back_forth < curr:
                    maxSpeaker1 = speaker1
                    maxSpeaker2 = speaker2
                    back_forth = curr


        print("\n\n\n-------------------- Graph Analysis --------------------\n")

        print(f"  Num distinct speakers: {len(vertices)}")
        print(f"    Num questions asked: {self.conn.getEdgeCount('asked_question')}")
        print(f"      Num answers given: {self.conn.getEdgeCount('answered_question')}\n")

        print(f"  Answered the most questions: {minSpeaker.get('v_id')} ({maxVal} answered)")
        print(f"     Asked the most questions: {maxSpeaker.get('v_id')} ({minVal} asked)\n")

        print(f"  Pair w/ most back-and-forth: {maxSpeaker1.get('v_id')} & {maxSpeaker2.get('v_id')}\n")


# This classes generates a wordcloud of most common spoken words

class MiscAnalysis:

    def __init__(self, config, path):
        nltk.download('punkt')
        nltk.download("stopwords")
        nltk.download("vader_lexicon")

        text = ""
        with open(path, 'r') as vtt:
            for line in vtt:
                match = re.search(r'^\d+[.].*', line)
                if not match: text += line.strip() + " "; continue

        self.words = word_tokenize(text)
        self.path = path


    def generateCloud(self):

        words_no_punc = []

        for word in self.words:
            if word.isalpha():
                words_no_punc.append(word.lower())

        stopwords_list = stopwords.words("english")
        stopwords_list.extend(["said","one","like","came","back"])

        clean_words = []

        for word in words_no_punc:
            if word not in stopwords_list:
                clean_words.append(word)

        print("\n\n\n-------------------- Visual Analysis --------------------")

        print(f"\n  Number of words excluding punctuation & stopwords: {len(clean_words)}\n")
        print("  *Visual frequency chart of top 10 meaningful words* (close to continue)")
        fdist = FreqDist(clean_words)
        fdist.plot(10)

        clean_words_string = " ".join(clean_words)
        wordcloud = WordCloud(background_color="white").generate(clean_words_string)

        print("  *Visual word cloud of most meaningful used words* (close to continue)")

        plt.figure(figsize = (10, 5))
        plt.imshow(wordcloud)
        plt.axis("off")
        plt.show()


    def basicAnalysis(self):
        print("\n\n\n-------------------- Basic Analysis --------------------")

        print(f"\n  Total number of words: {len(self.words)}\n")

        finder = nltk.collocations.TrigramCollocationFinder.from_words(self.words)
        trigram1, trigram2 = finder.ngram_fd.most_common(2)
        print(f"      1st common trigram: {' '.join(trigram1[0])} (Count: {trigram1[1]})")
        print(f"      2nd common trigram: {' '.join(trigram2[0])} (Count: {trigram2[1]})")

        sia = SentimentIntensityAnalyzer()
        sentiment = sia.polarity_scores(" ".join(self.words))
        print(f"\n      Positivity Score: {sentiment['pos']}")
        print(f"      Neutrality Score: {sentiment['neu']}")
        print(f"      Negativity Score: {sentiment['neg']}")


    def durationsSpoken(self):
        speakers = {} # Key: speaker, Value: list of intervals

        with open(self.path, 'r') as vtt:
            for line in vtt:
                match = re.search(r'^\d+[.].*', line)
                if not match: continue

                name = line.split(".")[1].strip()
                time = line.split(name)[-1].strip()

                start, end = time.split("->")

                start = start[1:].strip()
                end = end.strip()

                s_hr, s_min, s_sec = start.split(":")
                e_hr, e_min, e_sec = end.split(":")

                s_sec = int(s_hr) * 60 * 60 + int(s_min) * 60 + float(s_sec)
                e_sec = int(e_hr) * 60 * 60 + int(e_min) * 60 + float(e_sec)

                time_diff = round(e_sec - s_sec, 6)
                name = str(name).strip()

                if name not in speakers:
                    speakers[name] = [time_diff]
                elif name in speakers:
                    speakers[name].append(time_diff)

        most = ""; max_time = 0; least = ""; min_time = 0

        for speaker in speakers:
            curr_sum = sum(speakers[speaker])
            if (curr_sum > max_time):
                max_time = curr_sum
                most = speaker
            if (min_time == 0 or curr_sum < min_time):
                min_time = curr_sum
                least = speaker

        print("\n\n\n------------------- Duration Analysis -------------------")

        print(f"\n  Spoke the most: {most} ({round(max_time, 4)} sec)")
        print(f"     Spoke least: {least} ({round(min_time, 4)} sec)\n")

        for speaker in speakers:
            print(f"       - {speaker}: {len(speakers[speaker])} times, averaging {round(mean(speakers[speaker]), 4)} sec")
