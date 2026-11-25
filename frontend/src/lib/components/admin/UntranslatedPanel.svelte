<!--
	A work's "Not yet translated" section: every target language with no edition,
	where its translation job stands, and a Translate button where one can be
	filed. Shared by the book and sermon admin pages (backend `detail._untranslated`).
-->
<script lang="ts">
	import { JOB_TONE_CLASS, jobStatusMeta } from '$lib/adminActivity';
	import { auth } from '$lib/auth.svelte';
	import { createAdminTranslationJob, type AdminUntranslated } from '$lib/library-admin';

	let {
		kind,
		slug,
		untranslated
	}: { kind: 'book' | 'sermon'; slug: string; untranslated: AdminUntranslated } = $props();

	type Missing = AdminUntranslated['languages'][number];
	// A job filed from this page, by language: the stage it now holds, or the
	// error the POST answered. The list itself is the load's; this overlays it.
	let filed = $state<Record<string, { stage?: 'queued'; error?: string }>>({});
	let filing = $state<Record<string, boolean>>({});
	const stageOf = (m: Missing) => filed[m.code]?.stage ?? m.job_status;
	// A job can be filed when nothing is in flight: never filed, or one that
	// closed without shipping. The backend's duplicate guard is the real check.
	const canFile = (m: Missing) => {
		const st = stageOf(m);
		return (
			(st === 'none' || st === 'closed' || st === 'unknown') &&
			auth.can('translate', 'suggest', m.code)
		);
	};
	async function translate(m: Missing) {
		filing[m.code] = true;
		try {
			await createAdminTranslationJob({ type: kind, slug, language: m.code });
			filed[m.code] = { stage: 'queued' };
		} catch (e) {
			filed[m.code] = { error: e instanceof Error ? e.message : 'Could not file the job.' };
		} finally {
			filing[m.code] = false;
		}
	}
</script>

{#if untranslated.languages.length}
	<section
		id="untranslated"
		class="mt-8 scroll-mt-[calc(var(--appnav-h,0px)+1rem)] rounded-card border border-border bg-surface p-5"
	>
		<h2 class="text-h3">Not yet translated</h2>
		{#if untranslated.blocked}
			<p class="mt-1 text-small text-muted">
				This {kind} is under copyright, so no translation may be made of it.
			</p>
		{:else}
			<p class="mt-1 text-small text-muted">
				Where each language's translation job stands. Filing one opens a GitHub issue a worker picks
				up.
			</p>
		{/if}
		<ul class="mt-3 divide-y divide-border rounded-card border border-border">
			{#each untranslated.languages as m (m.code)}
				{@const st = stageOf(m)}
				<li class="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
					<span class="text-body text-text">
						{m.native_name} <span class="text-small text-muted">· {m.name} ({m.code})</span>
					</span>
					<span class="flex flex-wrap items-center gap-2 text-small">
						{#if st === 'none'}
							<span class="text-muted">Not filed</span>
						{:else}
							{@const js = jobStatusMeta(st, `${kind}:${slug}:${m.code}`)}
							<span
								class="rounded-full border px-2 py-0.5 text-micro font-semibold {JOB_TONE_CLASS[
									js.tone
								]}"
								title={js.hint}
							>
								{js.label}
							</span>
						{/if}
						{#if m.pr_url}<a
								href={m.pr_url}
								class="text-muted hover:text-accent"
								target="_blank"
								rel="noopener"
							>
								PR ↗
							</a>{/if}
						{#if m.issue_url}<a
								href={m.issue_url}
								class="text-muted hover:text-accent"
								target="_blank"
								rel="noopener"
							>
								issue ↗
							</a>{/if}
						{#if filed[m.code]?.error}<span class="text-danger">{filed[m.code].error}</span>{/if}
						{#if !untranslated.blocked && canFile(m)}
							<button
								class="btn btn-sm btn-ghost"
								onclick={() => translate(m)}
								disabled={filing[m.code]}
								aria-busy={filing[m.code] ? 'true' : undefined}
							>
								{#if filing[m.code]}<span class="btn-spinner" aria-hidden="true"
									></span>{/if}Translate
							</button>
						{/if}
					</span>
				</li>
			{/each}
		</ul>
	</section>
{/if}
