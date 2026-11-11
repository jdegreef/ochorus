import { error } from '@sveltejs/kit';
import { GLOSSARY_TERMS, isGlossaryTerm } from '$lib/glossary';
import { getWordPassages, type WordPassage } from '$lib/library-public';
import type { EntryGenerator, PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// One page per glossary term — the same list the index links and the sitemap
// advertises ($lib/glossary), so the three can't disagree.
export const entries: EntryGenerator = () => GLOSSARY_TERMS.map((term) => ({ term }));

export const load: PageLoad = async ({ params, fetch }) => {
	if (!isGlossaryTerm(params.term)) error(404, 'Not in the glossary');
	// The examples are the page's evidence, not its substance: the term and its
	// definition stand without them, so a failed fetch leaves the section out
	// rather than failing the page (or the build).
	let passages: WordPassage[] = [];
	try {
		passages = (await getWordPassages(params.term, fetch)).passages;
	} catch {
		passages = [];
	}
	return { term: params.term, passages };
};
