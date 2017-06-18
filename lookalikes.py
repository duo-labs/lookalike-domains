#!/usr/bin/env python
#
# lookalikes.py
# duo labs <labs@duo.com>
# all rights reserved, all wrongs reversed.
#

import sys, operator

def find_all(needle, haystack):
    start = 0
    while True:
        start = haystack.find(needle, start)
        if start == -1: return
        yield start
        start += len(needle)

def quadrantize(pos, domain):
    pos = pos + 1
    chunk = len(domain)/4.0
    if pos <= chunk*1:
        return 1
    elif pos <= chunk*2:
        return 2
    elif pos <= chunk*3:
        return 3
    else:
        return 4

def generate_homoglyphs(domain, naked, tld):
    # TODO: adjust total rank so it fits in well with other techniques
    # eyeball-ranked letter replacements
    replacers = [
        ('rn', 'm', 1.0), # rn and m are high!
        ('l', 't', 1.0), # l and t are high!
        ('r', 'i', 0.6), # r and i are medium, if you squint!
        ('n', 'm', 0.6), # n and m are medium
        ('d', 'cl', 0.6), # d and cl are medium, spacing stands out
        ('vv', 'w', 0.6), # vv and w are medium, spacing stands out
        ('l', 'i', 0.3), # l and i are medium/low, l is too tall and stands out
        ('j', 'i', 0.3), # j and i are low, j sticks out below
        ('l', '1', 0.3), # l and 1 are low, 1 stands out due to width 
        ('o', 'c', 0.3), # o and c are low
        ('u', 'v', 0.3), # u and v are low
        ('nn', 'm', 0.3), # nn and m are low
    ]
    # favor replacements that occur towards the middle of the domain
    # we just add the quadrant rank to the replacement rank to favor the ranking
    # quadrant rank order: 3rd, 2nd, 4th, 1st
    quadrant_rank = {
        1: 0.01,
        2: 0.03,
        3: 0.04,
        4: 0.02,
    }

    domains = []
    replacements = []

    # find all the candidate replacements
    for search, replace, rank in replacers:
        for pos in list(find_all(search, naked)):
            replacements.append((search, replace, pos, rank))
        for pos in list(find_all(replace, naked)):
            replacements.append((replace, search, pos, rank))

    # first pass of single replacements
    for find, replace, pos, rank in replacements:
        candidate = naked[:pos] + replace + naked[pos+len(find):]
        final_rank = rank + quadrant_rank[quadrantize(pos, naked)]
        domains.append(('%s.%s' % (candidate, tld), final_rank))

    # TODO: second pass of multiple replacements to provide more quantity
    # we could also do alternate tlds with single pass

    return domains

def generate_alttlds(domain, naked, tld):
    # tld tricks
    # preference: .com, .net, .org, .biz, .company
    # the tlds .co, .cm are not supported by R53
    domains = []

    alt_tlds = [
        ( 'com', 1.0 ),
        ( 'co', 0.9 ),
        ( 'cm', 0.9 ),
        ( 'net', 0.8 ),
        ( 'org', 0.8 ),
        ( 'io', 0.5 ),
        ( 'biz', 0.5 ),
        ( 'company', 0.5 ),
    ]
    for alt_tld, rank in alt_tlds:
        alt = '%s.%s' % (naked, alt_tld)
        domains.append((alt, rank))

    return domains

def generate_suffixes(domain, naked, tld):
    # prefix/suffix tricks (eg. -corp, -secure, -login)
    # preference: -secure, -login, -logon, -secure-login, -secure-logon
    domains = []

    suffixes = [
        ( '-secure', 0.8 ),
        ( '-login', 0.6 ),
        ( '-logon', 0.6 ),
        ( '-secure-login', 0.4 ),
        ( '-secure-logon', 0.4 ),
    ]
    for suffix, rank in suffixes:
        alt = '%s%s.%s' % (naked, suffix, tld)
        domains.append((alt, rank))

    prefixes = [
        ( 'secure-', 0.7 ),
        ( 'login-', 0.5 ),
        ( 'logon-', 0.5 ),
        ( 'secure-login-', 0.3 ),
        ( 'secure-logon-', 0.3 ),
    ]
    for prefix, rank in prefixes:
        alt = '%s%s.%s' % (prefix, naked, tld)
        domains.append((alt, rank))

    return domains

def check_availability(domain):
    # TODO: could wire up to registrar APIs (R53, etc)
    return True

def main(domain, limit=10):
    naked, _, tld = domain.rpartition('.')

    domains = {}
    candidates = {
        'alttlds': generate_alttlds(domain, naked, tld),
        'homoglyphs': generate_homoglyphs(domain, naked, tld),
        'suffixes': generate_suffixes(domain, naked, tld),
    }
    for kind in candidates.keys():
        domains[kind] = []

        # sort by the ranking score before checking availability
        ranked = sorted(candidates[kind], key=operator.itemgetter(1), reverse=True)

        for name, rank in ranked:
            if check_availability(name):
                domains[kind].append((name, rank))
            if len(domains[kind]) >= limit:
                break

    for key, val in candidates.iteritems():
        print '%s:' % key
        for domain, rank in val:
            print '  %s %s' % (domain, rank)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) > 2:
        print "Too many domain arguments given!"
        exit(1)
    else:
        print "Required domain argument not given!"
        exit(1)
