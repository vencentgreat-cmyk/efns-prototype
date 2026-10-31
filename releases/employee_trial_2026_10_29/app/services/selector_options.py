"""Presentation-only selector identities; never infer or change relationships."""
from collections import defaultdict


def unique_identity_options(items, *, reserved_labels=()):
    """Keep normal labels; disambiguate collisions with stable ID prefixes.

    Prefix width grows for the whole collision group, so results do not depend
    on query order, and prefixes shared by multiple IDs cannot overwrite one.
    """
    rows=list(dict.fromkeys((str(label), str(identity)) for label,identity in items))
    groups=defaultdict(set)
    for label,identity in rows:
        groups[label].add(identity)
    reserved=set(reserved_labels)
    occupied=set(groups)|reserved
    labels={}
    for label,identities in sorted(groups.items()):
        if len(identities)==1 and label not in reserved:
            labels[(label,next(iter(identities)))]=label
            continue
        for width in range(8,max(8,max(map(len,identities)))+1):
            proposed={identity:label+' · '+identity[:width] for identity in identities}
            if len(set(proposed.values()))==len(identities) and not (set(proposed.values())&occupied):
                break
        else:
            # A natural label may already equal the full-ID spelling. Use an
            # explicit ID marker, extending it deterministically if necessary.
            marker = 'id:'
            proposed = {identity:label+' · '+marker+identity for identity in identities}
            while set(proposed.values()) & occupied:
                marker += 'id:'
                proposed = {identity:label+' · '+marker+identity for identity in identities}
        for identity,display in proposed.items():
            labels[(label,identity)]=display
        occupied.update(proposed.values())
    return {labels[(label,identity)]:identity for label,identity in rows}
