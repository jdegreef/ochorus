import { loadLlmsData } from "$lib/llmsData";
import { buildLlmsTxt } from "$lib/llmsTxt";

export const prerender = true;

// The short AI-assistant map of the site (llmstxt.org); see $lib/llmsTxt.
export async function GET() {
  const body = buildLlmsTxt(await loadLlmsData(false));
  return new Response(body, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
