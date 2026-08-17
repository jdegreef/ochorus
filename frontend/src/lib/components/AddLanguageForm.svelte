<script lang="ts">
	/**
	 * Add a language to the registry — the admin's starting point for a new one.
	 *
	 * This form exists because starting a language used to mean editing Python
	 * and deploying: Arabic sat fully configured in the tree and invisible in the
	 * admin for months. What it writes is the row the translate_* commands read,
	 * so a language created here is immediately queueable for work.
	 *
	 * The glossary is required in full, and the term list comes from the API
	 * rather than being hardcoded here — it is the backend's contract, and a
	 * half-filled glossary is the expensive failure: the translator quietly
	 * renders the missing terms however it likes, chapter after chapter, and it
	 * all looks fine.
	 */
	import {
		createAdminLanguage,
		getAdminLanguageForm,
		type CreateLanguageResult,
		type LanguageSuggestion
	} from '$lib/library-admin';
	import { buildGlossaryPrompt, parseGlossaryReply } from '$lib/glossaryDraft';

	let { oncreated }: { oncreated?: (result: CreateLanguageResult) => void } = $props();

	let open = $state(false);
	let terms = $state<string[]>([]);
	let existing = $state<string[]>([]);
	let suggested = $state<LanguageSuggestion[]>([]);
	let showAll = $state(false);
	let loadError = $state('');

	let code = $state('');
	let name = $state('');
	let nativeName = $state('');
	let bibleCode = $state('');
	let bibleLabel = $state('');
	// Recorded when the Bible is CHOSEN, not remembered afterwards. The picker
	// already knows which suggestions are licensed (it shows "· attribution");
	// dropping that on the floor at create time is what left Hindi's CC-BY-SA
	// obligation living in a code comment instead of in the readiness check.
	let bibleLicence = $state('');
	let rtl = $state(false);
	let glossary = $state<Record<string, string>>({});

	let saving = $state(false);
	let error = $state('');
	let created = $state<CreateLanguageResult | null>(null);

	// --- Draft the glossary with Claude ---------------------------------------
	let pasted = $state('');
	let pasteNote = $state('');
	let pasteError = $state(false);
	let promptCopied = $state(false);

	async function copyPrompt() {
		const prompt = buildGlossaryPrompt({
			name,
			nativeName,
			bibleLabel,
			bibleCode,
			terms
		});
		try {
			await navigator.clipboard.writeText(prompt);
			promptCopied = true;
			setTimeout(() => (promptCopied = false), 2500);
		} catch {
			// Clipboard is permission-gated and blocked outright in some admin
			// contexts; drop the prompt into the paste box so it can be copied by
			// hand rather than silently doing nothing.
			pasted = prompt;
			pasteNote = 'Clipboard blocked — the prompt is in the box below; copy it from there.';
			pasteError = false;
		}
	}

	function applyPasted() {
		const r = parseGlossaryReply(pasted, terms);
		if (r.error) {
			pasteError = true;
			pasteNote = r.error;
			return;
		}
		// Merge rather than replace: a term already typed by hand is not
		// discarded by a reply that happens to omit it.
		glossary = { ...glossary, ...r.values };
		pasteError = r.filled.length === 0;
		const bits = [`Filled ${r.filled.length} of ${terms.length}.`];
		if (r.missing.length) bits.push(`Still empty: ${r.missing.join(', ')}.`);
		if (r.unknown.length) bits.push(`Ignored unknown: ${r.unknown.join(', ')}.`);
		pasteNote = bits.join(' ');
	}

	/** Fill the form from a suggestion. The glossary is still the admin's job —
	    it is the one part no catalogue can supply. */
	function pick(s: LanguageSuggestion) {
		code = s.code;
		name = s.name;
		nativeName = s.native_name;
		bibleCode = s.bible;
		bibleLabel = s.bible_label;
		bibleLicence = s.attribution_required ? s.licence : '';
		rtl = s.rtl;
	}

	const shown = $derived(showAll ? suggested : suggested.slice(0, 8));
	const normalized = $derived(code.trim().toLowerCase());
	const taken = $derived(normalized !== '' && existing.includes(normalized));
	const missing = $derived(terms.filter((t) => !(glossary[t] ?? '').trim()));
	const canSubmit = $derived(
		!saving &&
			normalized !== '' &&
			!taken &&
			name.trim() !== '' &&
			nativeName.trim() !== '' &&
			bibleCode.trim() !== '' &&
			missing.length === 0
	);

	async function toggle() {
		open = !open;
		if (!open || terms.length) return;
		try {
			const form = await getAdminLanguageForm();
			terms = form.glossary_terms;
			existing = form.existing;
			suggested = form.suggestions ?? [];
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		}
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!canSubmit) return;
		saving = true;
		error = '';
		try {
			const result = await createAdminLanguage({
				code: normalized,
				name: name.trim(),
				native_name: nativeName.trim(),
				bible_code: bibleCode.trim(),
				bible_label: bibleLabel.trim(),
				bible_licence: bibleLicence.trim(),
				rtl,
				glossary
			});
			created = result;
			existing = [...existing, normalized];
			oncreated?.(result);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			saving = false;
		}
	}

	function addAnother() {
		created = null;
		code = '';
		name = '';
		nativeName = '';
		bibleCode = '';
		bibleLabel = '';
		bibleLicence = '';
		rtl = false;
		glossary = {};
	}
</script>

<div class="mt-4 rounded-2xl border border-border bg-surface p-5">
	<button
		class="text-body font-semibold text-accent hover:underline"
		aria-expanded={open}
		onclick={toggle}
	>
		{open ? '−' : '+'} Add a language
	</button>

	{#if open}
		{#if loadError}
			<p class="mt-3 text-body text-gold">Couldn't load the form: {loadError}</p>
		{:else if created}
			<div class="mt-4 space-y-3">
				<p class="text-body">
					<span class="font-semibold text-accent">{created.language.name}</span> is in the
					registry as a draft — readers won't see it until you take it live.
				</p>
				{#if !created.bible_verified}
					<!-- Not a rejection: we couldn't ask, which is a different fact from
					     "the code is wrong", and the readiness check asks again later. -->
					<p class="text-small text-gold">{created.bible_note}</p>
				{/if}
				<ol class="list-decimal space-y-1 pl-5 text-small text-muted">
					{#each created.next_steps as step (step)}
						<li>{step}</li>
					{/each}
				</ol>
				<div class="flex gap-4">
					<a
						class="text-body font-semibold text-accent hover:underline"
						href="/admin/languages/{created.language.code}"
					>
						Open {created.language.name} →
					</a>
					<button class="text-body text-muted hover:text-text" onclick={addAnother}>
						Add another
					</button>
				</div>
			</div>
		{:else}
			<form class="mt-4 space-y-4" onsubmit={submit}>
				<p class="text-small text-muted">
					Creates a draft. Nothing is shown to readers until its checks pass and you
					press Go live on the language's page.
				</p>

				{#if suggested.length}
					<div class="rounded-lg border border-border bg-surface-2 p-3">
						<p class="text-small text-muted">
							<span class="font-medium text-text">Suggested next</span> — most spoken
							first, and only languages Take Root has a Bible for. Picking one fills
							everything below except the glossary.
						</p>
						<ul class="mt-2.5 grid gap-1.5 sm:grid-cols-2">
							{#each shown as s (s.code)}
								<li>
									<button
										type="button"
										class="w-full rounded-lg border border-border bg-bg px-2.5 py-2 text-left hover:border-accent"
										class:border-accent={normalized === s.code}
										onclick={() => pick(s)}
									>
										<span class="flex items-baseline justify-between gap-2">
											<span class="text-body text-text">{s.name}</span>
											<span class="shrink-0 text-[0.72rem] text-muted tabular-nums">
												{s.speakers_millions}M
											</span>
										</span>
										<span class="mt-0.5 flex items-baseline justify-between gap-2 text-[0.72rem] text-muted">
											<span dir="auto">{s.native_name}</span>
											<span class="shrink-0">
												{s.bible_label}{#if s.attribution_required}
													<span title="CC-BY — wants an attribution line">
														· attribution</span
													>{/if}
											</span>
										</span>
									</button>
								</li>
							{/each}
						</ul>
						{#if suggested.length > shown.length || showAll}
							<button
								type="button"
								class="mt-2 text-small text-accent hover:underline"
								onclick={() => (showAll = !showAll)}
							>
								{showAll ? 'Show fewer' : `Show all ${suggested.length}`}
							</button>
						{/if}
					</div>
				{/if}

				<div class="flex flex-wrap gap-4">
					<label class="text-small">
						<span class="mb-1 block text-muted">Code</span>
						<input
							class="w-24 rounded-lg border border-border bg-bg px-2 py-1 text-body"
							placeholder="hi"
							bind:value={code}
							required
						/>
					</label>
					<label class="text-small">
						<span class="mb-1 block text-muted">English name</span>
						<input
							class="w-44 rounded-lg border border-border bg-bg px-2 py-1 text-body"
							placeholder="Hindi"
							bind:value={name}
							required
						/>
					</label>
					<label class="text-small">
						<span class="mb-1 block text-muted">Native name</span>
						<input
							class="w-44 rounded-lg border border-border bg-bg px-2 py-1 text-body"
							placeholder="हिन्दी"
							bind:value={nativeName}
							required
						/>
					</label>
					<label class="flex items-center gap-2 self-end pb-1 text-small text-muted">
						<input type="checkbox" bind:checked={rtl} />
						Right-to-left script
					</label>
				</div>
				{#if taken}
					<p class="text-small text-gold">{normalized} is already in the registry.</p>
				{/if}

				<div class="border-t border-border pt-4">
					<h3 class="text-body font-semibold">Bible</h3>
					<p class="mb-2 text-small text-muted">
						Scripture quotations are taken verbatim from this translation, never from
						the model. Use a public-domain text where there is one — a CC-BY Bible puts
						an attribution obligation on every verse we render. Codes:
						<a class="underline" href="https://api.takeroot.bible" rel="noreferrer"
							>api.takeroot.bible</a
						>. The code is verified when you save.
					</p>
					<div class="flex flex-wrap gap-4">
						<label class="text-small">
							<span class="mb-1 block text-muted">Take Root code</span>
							<input
								class="w-40 rounded-lg border border-border bg-bg px-2 py-1 text-body"
								placeholder="irvhin"
								bind:value={bibleCode}
								required
							/>
						</label>
						<label class="text-small">
							<span class="mb-1 block text-muted">Label (shown in reports)</span>
							<input
								class="w-64 rounded-lg border border-border bg-bg px-2 py-1 text-body"
								placeholder="Indian Revised Version"
								bind:value={bibleLabel}
							/>
						</label>
					</div>
				</div>

				<div class="border-t border-border pt-4">
					<h3 class="text-body font-semibold">Theological glossary</h3>
					<p class="mb-3 text-small text-muted">
						Every term, in this language. These are pinned so the same doctrine is
						worded the same way in every book, sermon and biography — a partial
						glossary produces translations that drift term by term and look fine doing
						it.
					</p>
					<!-- Draft with Claude. There is no API key on the API service, so the
					     admin cannot call a model itself; rather than add a secret, a
					     per-call cost and a new failure mode, this hands you the prompt
					     and reads the answer back. The prompt names the Bible above,
					     because that is the wording the engine quotes verbatim — a
					     glossary that disagrees with its own Bible produces prose that
					     contradicts the verses beside it. -->
					<div class="mb-4 rounded-lg border border-border bg-surface-2 p-3">
						<div class="flex flex-wrap items-center gap-2">
							<button type="button" class="btn-soft text-small" onclick={copyPrompt} disabled={!name.trim()}>
								{promptCopied ? 'Prompt copied' : 'Copy prompt for Claude'}
							</button>
							<span class="text-small text-muted">
								{#if !name.trim()}
									Fill in the language name first.
								{:else}
									Run it in Claude, then paste the reply below.
								{/if}
							</span>
						</div>
						<textarea
							class="mt-2 w-full rounded-lg border border-border bg-bg px-2 py-1 font-mono text-small"
							rows="3"
							placeholder={'Paste Claude\'s reply here — the JSON object, fence and all'}
							bind:value={pasted}
						></textarea>
						<div class="flex flex-wrap items-center gap-2">
							<button type="button" class="btn-soft text-small" onclick={applyPasted} disabled={!pasted.trim()}>
								Fill the glossary
							</button>
							{#if pasteNote}
								<span class="text-small" class:text-accent={!pasteError} class:text-danger={pasteError}>
									{pasteNote}
								</span>
							{/if}
						</div>
					</div>

					<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
						{#each terms as term (term)}
							<label class="text-small">
								<span class="mb-1 block text-muted">{term}</span>
								<input
									class="w-full rounded-lg border border-border bg-bg px-2 py-1 text-body"
									bind:value={glossary[term]}
								/>
							</label>
						{/each}
					</div>
					{#if terms.length && missing.length}
						<p class="mt-2 text-small text-muted">
							{missing.length} of {terms.length} still to fill in.
						</p>
					{/if}
				</div>

				{#if error}
					<p class="text-body text-gold">{error}</p>
				{/if}

				<button
					class="rounded-full bg-accent px-4 py-1.5 text-small font-semibold text-accent-contrast disabled:opacity-50"
					type="submit"
					disabled={!canSubmit}
				>
					{saving ? 'Adding…' : 'Add language'}
				</button>
			</form>
		{/if}
	{/if}
</div>
