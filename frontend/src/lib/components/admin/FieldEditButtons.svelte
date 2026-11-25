<!--
	"Edit title / summary / …" for one book or sermon edition: each files a
	content-edit job (kind `field`) proposing new text, which a worker applies as
	one fixture edit the seeds carry live. The fields and their editors come from
	`EDITABLE_FIELDS` (the backend's FIELD_EDITS); nothing is edited in place.
-->
<script lang="ts">
	import QueueFixButton from '$lib/components/QueueFixButton.svelte';
	import { EDITABLE_FIELDS, fileFieldEditJob, type EditableField } from '$lib/library-admin';

	let {
		entity,
		slug,
		language,
		values
	}: {
		entity: EditableField['entity'];
		slug: string;
		language: string;
		/** The edition: each field's current text is read off it by name. */
		values: object;
	} = $props();
</script>

<div class="mt-1 flex flex-wrap items-start gap-x-3 gap-y-1 text-small">
	{#each EDITABLE_FIELDS[entity] as f (f.field)}
		{@const current = String((values as Record<string, unknown>)[f.field] ?? '')}
		<QueueFixButton
			label={f.label}
			seed={current}
			multiline={f.multiline}
			allowEmpty={f.field !== 'title'}
			fieldLabel="New {f.field.replace('_', ' ')}"
			saveLabel="Suggest"
			filedLabel="edit queued"
			submit={(next) =>
				fileFieldEditJob(
					{ entity, field: f.field, slug, language } as EditableField & {
						slug: string;
						language: string;
					},
					current,
					next
				)}
		/>
	{/each}
</div>
