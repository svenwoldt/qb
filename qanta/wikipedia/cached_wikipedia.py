import os
import pickle
from time import sleep
from requests import ConnectionError
from requests.exceptions import ReadTimeout

from unidecode import unidecode
import wikipedia
from wikipedia.exceptions import WikipediaException
from functional import seq

COUNTRY_SUB = ["History of ", "Geography of "]


class WikipediaPage:
    def __init__(self, content="", links=None, categories=None):
        self.content = content
        self.links = links if links is not None else []
        self.categories = categories if categories is not None else []


class CachedWikipedia:
    def __init__(self, location, country_list, write_dummy=True):
        """
        @param write_dummy If this is true, it writes an empty pickle if there
        is an error accessing a page in Wikipedia.  This will speed up future
        runs.
        """
        self.path = location
        self.cache = {}
        self.write_dummy = write_dummy
        self.countries = dict()
        if country_list:
            with open(country_list) as f:
                for line in f:
                    k, v = line.split('\t')
                    self.countries[k] = v

    def load_page(self, key: str):
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
            print("Connection error, waiting 1 minutes ...")
            sleep(60)
            print("trying again")
            return self[key]
        except ConnectionError:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 1 minutes ...")
            sleep(60)
            print("trying again")
            return self[key]
        except ValueError:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 1 minutes ...")
            sleep(60)
            print("trying again")
            return self[key]
        except WikipediaException:
            # Wait a while, see if the network comes back
            print("Connection error, waiting 1 minutes ...")
            sleep(60)
            print("trying again")
            return self.load_page(key)
        return raw

    def __getitem__(self, key: str):
        key = key.replace("_", " ")
        if key in self.cache:
            return self.cache[key]

        if "/" in key:
            filename = "%s/%s" % (self.path, key.replace("/", "---"))
        else:
            filename = "%s/%s" % (self.path, key)
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
            if key in self.countries:
                raw = [self.load_page("%s%s" % (x, self.countries[key])) for x in COUNTRY_SUB]
                raw.append(self.load_page(key))
                print("%s is a country!" % key)
            else:
                raw = [self.load_page(key)]

            raw = [x for x in raw if x is not None]
            sleep(.3)
            if raw:
                if len(raw) > 1:
                    print("%i pages for %s" % (len(raw), key))
                page = WikipediaPage(
                    "\n".join(unidecode(x.content) for x in raw),
                    seq(raw).map(lambda x: x.links).flatten().list(),
                    seq(raw).map(lambda x: x.categories).flatten().list())

                print("Writing file to %s" % filename)
                pickle.dump(page, open(filename, 'wb'),
                            protocol=pickle.HIGHEST_PROTOCOL)
            else:
                print("Dummy page for %s" % key)
                page = WikipediaPage()
                if self.write_dummy:
                    pickle.dump(page, open(filename, 'wb'),
                                protocol=pickle.HIGHEST_PROTOCOL)

        self.cache[key] = page
        return page
