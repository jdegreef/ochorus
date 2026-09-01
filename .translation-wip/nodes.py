"""Chapter node helper for the uk book pipeline.

Two jobs:
  * replace ONLY text nodes, so the tag sequence can never drift;
  * expand {{BOOK C:V}} tokens verbatim from the parsed Kulish Bible, so a
    verse is never typed from memory. That defect is invisible to the tag
    gate and only shows in the word count if the length happens to change.
"""
import json,re,sys
SPLIT=re.compile(r'(<[^>]+>)')
VERSE=re.compile(r'\{\{([1-3A-Z]{3} \d+:\d+)(?:\|([0-9]+(?:-[0-9]+)?))?([.~^+]*)\}\}')
BIBLE=json.load(open('bible_uk.json'))

# Typos in the ebible ukr_pan text, corrected against Kulish's own usage
# elsewhere in the SAME file.  Each entry must cite the count that proves it.
FIXES={
  # "спаннєм" (=sleeping) is a hapax; Kulish writes "спасеннєм" (=salvation)
  # in the other 14 places the word occurs.  ISA 25:9 is the odd one out.
  'ISA 25:9': ('спаннєм','спасеннєм'),
}
for _k,(_a,_b) in FIXES.items():
    assert _a in BIBLE[_k], _k
    BIBLE[_k]=BIBLE[_k].replace(_a,_b)

def expand(t):
    """{{PSA 25:5}} whole verse | |a-b word range | |n n-th ;-clause.
    Trailing flags touch ONLY the fragment's edges, never a word: `.` ends it
    with a full stop, `~` drops the trailing mark, `^`/`+` lower- or upper-case the
    leading letter (a verse boundary landing mid-sentence, or the reverse)."""
    def one(m):
        key,part,flag=m.group(1),m.group(2),m.group(3)
        if key not in BIBLE: raise SystemExit("no such verse: "+key)
        v=BIBLE[key]
        if part and '-' in part:                      # word range, 1-based inclusive
            a,b=(int(x) for x in part.split('-'))
            w=v.split()
            if b>len(w): raise SystemExit(f"{key} has {len(w)} words, wanted {b}")
            v=" ".join(w[a-1:b])
        elif part:                                     # ;-clause, 1-based
            bits=re.split(r'; ',v); i=int(part)-1
            if i>=len(bits): raise SystemExit(f"{key} has {len(bits)} clauses, wanted {part}")
            v=bits[i]
        if '^' in flag: v=v[0].lower()+v[1:]       # verse-start capital, mid-sentence
        if '+' in flag: v=v[0].upper()+v[1:]       # fragment opening a sentence
        if '.' in flag or '~' in flag:              # boundary punctuation only
            v=v.rstrip(' .,;:!?')
            if '.' in flag: v+='.'
        return v
    return VERSE.sub(one,t)

def load(slug,n):
    d=json.load(open(f'uk/{slug}/ch{n:02d}.json'))
    return d, SPLIT.split(d['body_html'])

def show(slug,n):
    d,p=load(slug,n)
    print(f"=== {slug} ch{n:02d} | {d['title']} | {d['word_count']}w | "
          f"{sum(1 for i,x in enumerate(p) if i%2==1)} tags")
    for i,x in enumerate(p):
        if i%2==0 and x.strip(): print(f"[{i}] {' '.join(x.split())}")

def write(slug,n,T,title):
    d,p=load(slug,n)
    todo=[i for i,x in enumerate(p) if i%2==0 and x.strip()]
    missing=[i for i in todo if i not in T]
    if missing: raise SystemExit(f"ch{n:02d}: untranslated nodes {missing}")
    json.dump({str(k):v for k,v in T.items()},                 # keep the source,
              open(f'uk/{slug}/src{n:02d}.json','w',encoding='utf-8'),  # tokens and all
              ensure_ascii=False,indent=1,sort_keys=True)
    for i,t in T.items(): p[i]=expand(t)
    body="".join(p)
    json.dump({"title":expand(title),"body_html":body},
              open(f'uk/{slug}/draft{n:02d}.json','w',encoding='utf-8'),
              ensure_ascii=False,indent=1)
    # per-chapter verbatim audit: every «…» of any length must be Kulish or prose
    flat=re.sub(r'<[^>]+>',' ',body)
    # a token's fragment carries its own punctuation; typing more doubles it,
    # and the tag gate cannot see it.  ch08-ch11 shipped ".!»" before this ran.
    for m in re.finditer(r'[.,;:!?]\s*[«»]?\s*[.,;:!?]',flat):
        if set(m.group(0))<={'.',' '}: continue        # spaced ellipsis
        if flat[max(0,m.start()-4):m.start()+1]=='марг.': continue   # abbreviation
        raise SystemExit(f"ch{n:02d}: doubled punctuation "
                         f"{flat[max(0,m.start()-40):m.end()+10]!r}")
    hay=" || ".join(BIBLE.values()).lower()   # `+`/`^` only touch case
    bad=[]
    for m in re.finditer(r'«([^»]{25,})»',flat):
        s=re.sub(r'\s+',' ',m.group(1)).strip(' .,;:!?')
        if s[:40].lower() not in hay: bad.append(s[:70])
    return len(todo), bad

if __name__=='__main__': show(sys.argv[1],int(sys.argv[2]))
