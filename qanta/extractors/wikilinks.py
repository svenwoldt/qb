from collections import defaultdict
from xml.etree import ElementTree
import argparse
from glob import glob
from math import log

from wikipedia.exceptions import PageError
from util.cached_wikipedia import CachedWikipedia
from clm.lm_wrapper import kGOODCHAR
from qanta.extractors.abstract import FeatureExtractor


class WikiLinks(FeatureExtractor):
    def __init__(self,
                 xml_location="data/wikifier/data/output",
                 wikipedia="data/wikipedia",
                 country_list='data/country_list.txt'):
        super(WikiLinks, self).__init__()
        self.name = "wikilinks"
        self._location = xml_location
        self._links = defaultdict(dict)
        self._wiki = CachedWikipedia(wikipedia, country_list)
        self._cache = -1
        self._matches = None

    def set_metadata(self, answer, category, qnum, sent, token, guesses, fold):
        FeatureExtractor.set_metadata\
          (self, answer, category, qnum, sent, token, guesses, fold)
        if qnum not in self._links:
            self.load_xml(qnum)

    def vw_from_title(self, title, text):
        if hash(text) != self._cache:
            self._cache = hash(text)
            self._matches = set()

            for ii in range(self._sent):
                self._matches = self._matches | \
                    set(x[0] for x in
                        self._links[self._qnum].get(ii, {}).values())

            for jj in self._links[self._qnum].get(self._sent, []):
                title, pos, index, score = \
                    self._links[self._qnum][self._sent][jj]
                if self._token > pos:
                    self._matches.add(title)

        total = 0
        matches = ["|%s" % self.name]
        display_title = "".join(x for x in kGOODCHAR.findall(title) if x)
        bad = set()
        for ii in [x for x in self._matches]:
            try:
                page = self._wiki[ii]
            except PageError:
                bad.add(ii)
                continue

            if title in page.links:
                norm = "".join(x for x in kGOODCHAR.findall(ii) if x)
                matches.append("%s_%s" % (norm, display_title))
                total += 1
        for ii in bad:
            self._matches.remove(ii)

        matches.append("Total:%f" % log(1 + total))
        return " ".join(matches)

    def load_xml(self, question):
        for ii in glob("%s/%i-*.txt.wikification.tagged.full.xml" %
                        (self._location, question)):
            sentence = int(ii.split(".txt.wikification")[0].rsplit("-", 1)[-1])
            tree = ElementTree.parse(ii)
            root = tree.getroot()

            # text = tree.find("InputText").text
            # print(text)

            for child in root[2].findall('Entity'):
                surface = child.find("EntitySurfaceForm").text
                start = int(child.find("EntityTextStart").text)
                end = int(child.find("EntityTextEnd").text)

                entity = child.find("TopDisambiguation")
                page = entity.find("WikiTitle").text
                id = entity.find("WikiTitleID").text
                score = float(entity.find("RankerScore").text)

                if sentence not in self._links[question]:
                    self._links[question][sentence] = {}
                self._links[question][sentence][surface] = \
                    (page, start, id, score)

    def features(self, question, candidate):
        pass

    def guesses(self, question):
        pass

    def vw_from_score(self, results):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument("--xml_location", type=str,
                        default="data/wikifier/data/output",
                        help="Where we write output file")
    flags = parser.parse_args()

    wl = WikiLinks(flags.xml_location)

    wl.load_xml(700000024)
    wl.set_metadata("", "", 700000024, 10, 0, 50, "expo")
    print(wl._qnum)
    print(wl.vw_from_title("Yukio Mishima", ""))
