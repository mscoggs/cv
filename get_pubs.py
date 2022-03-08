#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
from operator import itemgetter
import re
import ads
from utf8totex import utf8totex
from titlecase import titlecase
from tqdm import tqdm
import numpy as np
import time
import sys
import numpy as np
__all__ = ["get_papers"]


def title_callback(word, **kwargs):
    if "\\" in word:
        return word
    else:
        return None


def manual_edits(paper):
    print(paper.title, paper.doctype)
    if("Flare" in paper.title[0]):
        paper.doctype = "note"
    print(paper.doctype)
    return paper


def format_title(arg):
    """
    Customized!

    """

    # Do the conversion
    arg = utf8totex(arg)

    # Handle subscripts
    arg = re.sub("<SUB>(.*?)</SUB>", r"$_\1$", arg)

    # Fudge O2 paper
    arg = re.sub("O2Buildup", r"O$_2$ Buildup", arg)

    # Capitalize!
    arg = titlecase(arg, callback=title_callback)

    return arg


def format_authors(authors):
    """
    Customized!

    """

    # Do the conversion
    authors = list(map(utf8totex, authors))

    # Abbreviate names. This drops middle
    # initials -- should eventually fix this.
    for i, author in enumerate(authors):
        match = re.match("^(.*?),\s(.*?)$", author)
        if match is not None:
            first, last = match.groups()
            authors[i] = "%s, %s." % (first, last[0])

    return authors



def get_papers(author, count_cites=True):
    ads.config.token = os.getenv("ADS_DEV_KEY", "")
    papers = list(
        ads.SearchQuery(
            author=author,
            fl=[
                "id",
                "title",
                "author",
                "doi",
                "year",
                "pubdate",
                "pub",
                "volume",
                "page",
                "identifier",
                "doctype",
                "citation_count",
                "bibcode",
                "citation",
            ],
            max_pages=100,
        )
    )
    dicts = []

    # Count the citations as a function of time
    citedates = []

    # Save bibcodes for later
    bibcodes = []

    # Save papers that cite me
    if os.path.exists("papers_that_cite_me.json"):
        with open("papers_that_cite_me.json", "r") as f:
            papers_that_cite_me = json.load(f)
    else:
        papers_that_cite_me = {}

    for paper in tqdm(papers):
        index = [idx for idx, s in enumerate(paper.author) if 'coggins' in s]
        if(len(index)> 1):
            print("too many coggins in this list??")
            for ind in index:
                print(paper.author[ind])
            exit(0)
        my_name = paper.author[index[0]]
        if("T" not in my_name): continue
        # if not (
        #     ("Scoggins, M. T." in paper.author) or
        #     ("Scoggins, M. T." in paper.author) or
        #     ("Scoggins, Matthew T" in paper.author)
        # ):
        #     continue

        paper = manual_edits(paper)

        aid = [
            ":".join(t.split(":")[1:])
            for t in paper.identifier
            if t.startswith("arXiv:")
        ]
        for t in paper.identifier:
            if len(t.split(".")) != 2:
                continue
            try:
                list(map(int, t.split(".")))
            except ValueError:
                pass
            else:
                aid.append(t)
        try:
            page = int(paper.page[0])
        except ValueError:
            page = None
            if paper.page[0].startswith("arXiv:"):
                aid.append(":".join(paper.page[0].split(":")[1:]))
        except TypeError:
            page = None

        # Get citation dates
        if count_cites and paper.citation is not None:
            for i, bibcode in enumerate(paper.citation):
                try:
                    if bibcode in papers_that_cite_me.keys():
                        date = papers_that_cite_me[bibcode]
                    else:
                        cite = list(ads.SearchQuery(bibcode=bibcode, fl=["pubdate"]))[0]
                        date = int(cite.pubdate[:4]) + int(cite.pubdate[5:7]) / 12.0
                        papers_that_cite_me[bibcode] = date
                    citedates.append(date)
                except IndexError:
                    pass

        # Save bibcode
        bibcodes.append(paper.bibcode)

        dicts.append(
            dict(
                doctype=paper.doctype,
                authors=format_authors(paper.author),
                year=paper.year,
                pubdate=paper.pubdate,
                doi=paper.doi[0] if paper.doi is not None else None,
                title=format_title(paper.title[0]),
                pub=paper.pub,
                volume=paper.volume,
                page=page,
                arxiv=aid[0] if len(aid) else None,
                citations=paper.citation_count,
                url="http://adsabs.harvard.edu/abs/" + paper.bibcode,
            )
        )

    if count_cites:
        # Sort the cite dates
        citedates = sorted(citedates)
        np.savetxt("citedates.txt", citedates, fmt="%.3f")

    # Save bibcodes
    with open("bibcodes.txt", "w") as f:
        for bibcode in bibcodes:
            print(bibcode, file=f)

    # Save papers that cite me
    with open("papers_that_cite_me.json", "w") as f:
        json.dump(papers_that_cite_me, f)

    return sorted(dicts, key=itemgetter("pubdate"), reverse=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clobber":
        clobber = True
    else:
        clobber = False
    if clobber or not os.path.exists("pubs.json"):
        papers = get_papers("Scoggins, m", count_cites=True)
        with open("pubs.json", "w") as f:
            json.dump(papers, f, sort_keys=True, indent=2, separators=(",", ": "))
    else:
        print("Using cached pubs.")
