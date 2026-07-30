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
		type CreateLanguageResult
	} from '$lib/library-admin';

	let { oncreated }: { oncreated?: (result: CreateLanguageResult) => void } = $props();

	let open = $state(false);
	let terms = $state<string[]>([]);
	let existing = $state<string[]>([]);
	let loadError = $state('');

	let code = $state('');
	let name = $state('');
	let nativeName = $state('');
	let bibleCode = $state('');
	let bibleLabel = $state('');
	let rtl = $state(false);
	let glossary = $state<Record<string, string>>({});

	let saving = $state(false);
	let error = $state('');
	let created = $state<CreateLanguageResult | null>(null);

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
								placeholder="hin-irv"
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
