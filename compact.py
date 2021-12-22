"""
Script for turning VTT transcripts, e.g. those created by Zoom when you
record a meeting, into a denser format with less redundant information.

Created by: Will Larson (GitHub: lethain)
Original Source: https://github.com/lethain/vtt_compactor (unmodified usage)

"""

import argparse


class Segment:
    def __init__(self):
        self.num = 0
        self.speaker = None
        self.start = ""
        self.end = ""
        self.text = ""


    def time(self, txt):
        self.start, self.end = txt.split(' --> ')

    def is_complete(self):
        return self.num and self.speaker and  self.text

    def __repr__(self):
        return "Segment(%s, %s, %s, text: %s)" % (self.num, self.speaker, self.start, len(self.text))


def segments(fd):
    segments = []
    seg = Segment()
    for line in fd:
        try:
            if seg.is_complete():
                segments.append(seg)
                seg = Segment()
            line = line.strip()
            if line and line != "WEBVTT":
                if not seg.num:
                    seg.num = int(line)
                elif not seg.start:
                    seg.time(line)
                elif seg.speaker is None:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        seg.speaker, seg.text =  parts
                    elif len(parts) == 1:
                        # this happens sometimes for unclear reasons
                        seg.speaker = "OMITTED"
                        seg.text = parts[0]
                    seg.text = seg.text.strip()
        except Exception as e:
            print("couldn't parse: %s" % (line,))
            raise(e)
    return segments


def compact(segs):
    chunks = []
    if len(segs) == 0:
        return chunks

    chunk = segs[0]
    for seg in segs[1:]:
        if seg.speaker == chunk.speaker:
            chunk.text += "\n" + seg.text
            chunk.end = seg.end
        else:
            chunks.append(chunk)
            chunk = seg
    chunks.append(chunk)
    return chunks


def main_compact(filepath):

    new_dest = "b_cmt_transcripts/"
    new_path = new_dest + (filepath.split(".vtt")[0]+"_CMT.vtt").split("/")[1]

    with open(new_path, 'w') as dest:
        with open(filepath, 'r') as fin:
            segs = segments(fin)
            chunks = compact(segs)
            for chunk in chunks:
                print("%s. %s. %s -> %s\n\n%s\n" % (chunk.num, chunk.speaker, chunk.start, chunk.end, chunk.text), file=dest)
