"""Conservative literal alignment; no synonym matching or invented source words."""
import re


def align_quote(quote,text):
    """Copy an existing lexical sequence, preserving actual source punctuation.

    Full token sequences must match. For an explicit ellipsis, a single literal
    fragment may be used as the short excerpt; the omitted fragments are never
    joined. This is a location aid, not an entailment judgment.
    """
    if quote and quote in text and 2<=len(quote.split())<=14:
        return {'quote':quote,'raw_quote_exact':True,'span_method':'verbatim model span'}
    words=list(re.finditer(r'\w+',text));tokens=[m.group().casefold() for m in words]
    fragments=re.split(r'\.{2,}|…',quote)
    for fragment in sorted(fragments,key=lambda x:-len(re.findall(r'\w+',x))):
        wanted=[m.group().casefold() for m in re.finditer(r'\w+',fragment)]
        if len(wanted)<(4 if len(fragments)>1 else 2):continue
        for index in range(len(tokens)-len(wanted)+1):
            if tokens[index:index+len(wanted)]==wanted:
                end_index=index+min(10,len(wanted))-1
                span=text[words[index].start():words[end_index].end()]
                return {'quote':span,'raw_quote_exact':False,'original_generated_quote':quote,
                        'span_method':'Contiguous lexical sequence copied from source; punctuation/length normalized'+('; single fragment selected from explicit ellipsis' if len(fragments)>1 else '')}
    return None


def locate_excerpt(claim,proposed_quote,text):
    """Retrieve a literal navigation excerpt when the model supplied a paraphrase.

    This is explicitly not a verified supporting quotation. The full source
    paragraph and claim remain necessary for an entailment review.
    """
    ignored=set('the a an and or of to in at on by from is are was were be as that with his her their its has have had this for not it'.split())
    terms={w.casefold() for w in re.findall(r'\w+',claim+' '+proposed_quote)}-ignored
    words=list(re.finditer(r'\S+',text));best=None
    for start in range(len(words)):
        end=min(start+12,len(words));span=text[words[start].start():words[end-1].end()]
        found={w.casefold() for w in re.findall(r'\w+',span)}&terms
        score=(len(found),-start)
        if best is None or score>best[0]:best=(score,span)
    if best is None or best[0][0]<2:return None
    return {'quote':best[1],'raw_quote_exact':False,'original_generated_quote':proposed_quote,
            'span_method':'Source-exact lexical navigation excerpt; generated quote was a paraphrase; NOT a verified supporting quotation',
            'excerpt_terms_matched':best[0][0],'entailment_review_required':True}
