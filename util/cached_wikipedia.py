import os
import cPickle as pickle
import time
from time import sleep
from requests import ConnectionError
from requests.exceptions import ReadTimeout
from itertools import chain
from math import log

from unidecode import unidecode
import wikipedia, fileinput
from wikipedia.exceptions import WikipediaException

kCOUNTRY_SUB = ["History of ", "Geography of "]


class LinkResult:
    def __init__(self, text_freq=0, link_freq=0, early=0):
        self.text_freq = text_freq
        self.link_freq = link_freq
        self.early = early

    def componentwise_max(self, lr):
        self.text_freq = max(self.text_freq, lr.text_freq)
        self.link_freq = max(self.link_freq, lr.link_freq)
        self.early = max(self.early, lr.early)

    def any(self):
        """
        Did we find anything on any metric
        """
        return any(x > 0.0 for x in
                   [self.text_freq, self.link_freq, self.early])


class WikipediaPage:
    def __init__(self, content="", links=[], categories=[]):
        self.content = content
        self.links = links
        self.categories = categories

    def weighted_link(self, other_page):

        # Get the number of times it's mentioned in text
        no_disambiguation = other_page.split("(")[0].strip()
        if len(self.content) > 0:
            text_freq = self.content.count(no_disambiguation)
            text_freq *= len(no_disambiguation) / float(len(self.content))
        else:
            text_freq = 0.0

        # How many total links are there, divide by that number
        if other_page in self.links:
            link_freq = 1.0 / float(len(self.links))
        else:
            link_freq = 0.0

        # How early is it mentioned in the page
        early = self.content.find(no_disambiguation)
        if early > 0:
            early = 1.0 - early / float(len(self.content))
        else:
            0.0

        return LinkResult(text_freq, link_freq, early)


class CachedWikipedia:
    def __init__(self, location, country_list, write_dummy=True):
        """
        @param write_dummy If this is true, it writes an empty pickle if there
        is an error accessing a page in Wikipedia.  This will speed up future
        runs.
        """
        self._path = location
        self._cache = {}
        self._write_dummy = write_dummy
        if country_list:
            self._countries = dict(x.split('\t') for x in open(country_list))
        else:
            self._countries = dict()

    @staticmethod
    def load_page(key):
        print("Loading %s" % key)
        try:
            raw = wikipedia.page(key, preload=True)
            print(unidecode(raw.content[:80]))
            print(unidecode(str(raw.links)[:80]))
            print(unidecode(str(raw.categories)[:80]))
        except KeyError:
            print("Key error")
            raw = None
        except wikipedia.exceptions.DisambiguationError:
            print("Disambig error!")
            raw = None
        except wikipedia.exceptions.PageError:
            print("Page error!")
            raw = None
        except ReadTimeout:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 10 minutes ...")
            sleep(600)
            print("trying again")
            return CachedWikipedia.load_page(key)
        except ConnectionError:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 10 minutes ...")
            sleep(600)
            print("trying again")
            return CachedWikipedia.load_page(key)
        except ValueError:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 10 minutes ...")
            sleep(600)
            print("trying again")
            return CachedWikipedia.load_page(key)
        except WikipediaException:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 10 minutes ...")
            sleep(600)
            print("trying again")
            return CachedWikipedia.load_page(key)
        return raw

    def __getitem__(self, key):
        key = key.replace("_", " ")
        if key in self._cache:
            return self._cache[key]

        if "/" in key:
            filename = "%s/%s" % (self._path, key.replace("/", "---"))
        else:
            filename = "%s/%s" % (self._path, key)
        page = None
        if os.path.exists(filename):
            try:
                page = pickle.load(open(filename, 'rb'))
            except pickle.UnpicklingError:
                page = None
            except AttributeError:
                print("Error loading %s" % key)
                page = None
            except ImportError:
                print("Error importing %s" % key)
                page = None

        if page is None:
            if key in self._countries:
                raw = [CachedWikipedia.load_page("%s%s" %
                                                 (x, self._countries[key]))
                                                  for x in kCOUNTRY_SUB]
                raw.append(CachedWikipedia.load_page(key))
                print("%s is a country!" % key)
            else:
                raw = [CachedWikipedia.load_page(key)]

            raw = [x for x in raw if not x is None]

            sleep(.3)
            if raw:
                if len(raw) > 1:
                    print("%i pages for %s" % (len(raw), key))
                page = WikipediaPage("\n".join(unidecode(x.content) for
                                               x in raw),
                                     [y for y in
                                      x.links
                                      for x in raw],
                                     [y for y in
                                      x.categories
                                      for x in raw])

                print("Writing file to %s" % filename)
                pickle.dump(page, open(filename, 'wb'),
                            protocol=pickle.HIGHEST_PROTOCOL)
            else:
                print("Dummy page for %s" % key)
                page = WikipediaPage()
                if self._write_dummy:
                    pickle.dump(page, open(filename, 'wb'),
                                protocol=pickle.HIGHEST_PROTOCOL)

        self._cache[key] = page
        return page

if __name__ == "__main__":
    cw = CachedWikipedia("data/wikipedia", "data/country_list.txt")
    for ii in ["Camille_Saint-Saens", "Napoleon", "Langston Hughes", "Whigs_(British_political_party)", "Carthage", "Stanwix", "Lango people", "Lango language (Uganda)", "Keokuk", "Burma", "United Kingdom"]:
        print("~~~~~")
        print(ii)
        start = time.time()
        print cw[ii].content[:80]
        print str(cw[ii].links)[:80]
        print(time.time() - start)
