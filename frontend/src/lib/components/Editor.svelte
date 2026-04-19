<script lang="ts">
	import { onMount } from 'svelte';
	import { basicSetup } from 'codemirror';
	import { EditorView } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { html } from '@codemirror/lang-html';
	import { css } from '@codemirror/lang-css';
	import { oneDark } from '@codemirror/theme-one-dark';

	let {
		language,
		value = '',
		readonly = false,
		onChange,
		onCopyAttempt,
	}: {
		language: 'html' | 'css';
		value?: string;
		readonly?: boolean;
		onChange: (value: string) => void;
		onCopyAttempt?: () => void;
	} = $props();

	let container: HTMLDivElement;

	const noPasteCopyExtension = EditorView.domEventHandlers({
		paste: (e) => { e.preventDefault(); onCopyAttempt?.(); return true; },
		copy:  (e) => { e.preventDefault(); onCopyAttempt?.(); return true; },
		cut:   (e) => { e.preventDefault(); onCopyAttempt?.(); return true; },
	});

	const readOnlyCompartment = new Compartment();

	onMount(() => {
		let debounceTimer: ReturnType<typeof setTimeout> | null = null;

		const langExtension = language === 'html' ? html() : css();

		const extensions = [
			basicSetup,
			oneDark,
			langExtension,
			noPasteCopyExtension,
			readOnlyCompartment.of(EditorState.readOnly.of(readonly)),
			EditorView.updateListener.of((update) => {
				if (update.docChanged) {
					if (debounceTimer !== null) clearTimeout(debounceTimer);
					debounceTimer = setTimeout(() => {
						onChange(update.state.doc.toString());
					}, 300);
				}
			}),
		];

		const view = new EditorView({
			state: EditorState.create({ doc: value, extensions }),
			parent: container,
		});

		// Document-level capture: blocks paste/copy when editor is not focused
		const block = (e: Event) => { e.preventDefault(); onCopyAttempt?.(); };
		document.addEventListener('paste', block, true);
		document.addEventListener('copy',  block, true);

		// Reactively update readOnly when prop changes
		$effect(() => {
			view.dispatch({ effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(readonly)) });
		});

		return () => {
			if (debounceTimer !== null) clearTimeout(debounceTimer);
			document.removeEventListener('paste', block, true);
			document.removeEventListener('copy',  block, true);
			view.destroy();
		};
	});
</script>

<div bind:this={container} class="h-full w-full overflow-auto"></div>
