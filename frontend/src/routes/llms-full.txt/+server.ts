import { loadLlmsData } from '$lib/llmsData';
import { buildLlmsFullTxt } from '$lib/llmsTxt';

export const prerender = true;

// The long index: llms.txt plus every English book and sermon; see $lib/llmsTxt.
export async function GET() {
	const body = buildLlmsFullTxt(await loadLlmsData(true));
	return new Response(body, {
		headers: { 'content-type': 'text/plain; charset=utf-8' }
	});
}
