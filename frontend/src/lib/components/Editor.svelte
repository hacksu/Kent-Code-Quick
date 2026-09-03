<script lang="ts">
	import { onMount } from 'svelte';
	import { basicSetup } from 'codemirror';
	import { EditorView, keymap } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { indentWithTab } from '@codemirror/commands';
	import { html } from '@codemirror/lang-html';
	import { css } from '@codemirror/lang-css';
	import { javascript } from '@codemirror/lang-javascript';
	import { oneDark } from '@codemirror/theme-one-dark';

	let {
		language,
		value = '',
		readonly = false,
		blockCopyPaste = true,
		allowInternalClipboard = true,
		onChange,
		onCopyAttempt,
	}: {
		language: 'html' | 'css' | 'js';
		value?: string;
		readonly?: boolean;
		blockCopyPaste?: boolean;
		allowInternalClipboard?: boolean;
		onChange: (value: string) => void;
		onCopyAttempt?: () => void;
	} = $props();

	let container: HTMLDivElement;
	let view: EditorView;
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	// svelte-ignore state_referenced_locally
	let lastReportedValue = value;

	export function flush(): void {
		if (debounceTimer === null) return;
		clearTimeout(debounceTimer);
		debounceTimer = null;
		const v = view.state.doc.toString();
		lastReportedValue = v;
		onChange(v);
	}

	let internalClipboard = '';

	function selectedText(view: EditorView): string {
		const { from, to } = view.state.selection.main;
		return view.state.sliceDoc(from, to);
	}

	const noPasteCopyExtension = EditorView.domEventHandlers({
		copy: (e, view) => {
			if (!blockCopyPaste) return false;
			if (allowInternalClipboard) { internalClipboard = selectedText(view); return false; }
			e.preventDefault();
			onCopyAttempt?.();
			return true;
		},
		cut: (e, view) => {
			if (!blockCopyPaste) return false;
			if (allowInternalClipboard) { internalClipboard = selectedText(view); return false; }
			e.preventDefault();
			onCopyAttempt?.();
			return true;
		},
		paste: (e) => {
			if (!blockCopyPaste) return false;
			const pasted = e.clipboardData?.getData('text/plain') ?? '';
			if (allowInternalClipboard && pasted !== '' && pasted === internalClipboard) return false;
			e.preventDefault();
			onCopyAttempt?.();
			return true;
		},
	});

	const readOnlyCompartment = new Compartment();
	const langCompartment = new Compartment();

	onMount(() => {
		view = new EditorView({
			state: EditorState.create({
				doc: value,
				extensions: [
					basicSetup,
					oneDark,
					keymap.of([indentWithTab]),
					langCompartment.of(language === 'html' ? html() : language === 'css' ? css() : javascript()),
					noPasteCopyExtension,
					readOnlyCompartment.of(EditorState.readOnly.of(readonly)),
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							const v = update.state.doc.toString();
							lastReportedValue = v;
							if (debounceTimer !== null) clearTimeout(debounceTimer);
							debounceTimer = setTimeout(() => { debounceTimer = null; onChange(v); }, 300);
						}
					}),
				],
			}),
			parent: container,
		});

		$effect(() => {
			view.dispatch({ effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(readonly)) });
		});

		$effect(() => {
			const langExt = language === 'html' ? html() : language === 'css' ? css() : javascript();
			view.dispatch({ effects: langCompartment.reconfigure(langExt) });
		});

		$effect(() => {
			if (value !== lastReportedValue) {
				flush();
				lastReportedValue = value;
				view.dispatch({
					changes: { from: 0, to: view.state.doc.length, insert: value },
				});
			}
		});

		return () => {
			if (debounceTimer !== null) clearTimeout(debounceTimer);
			view.destroy();
		};
	});
</script>

<div bind:this={container} class="h-full w-full overflow-auto"></div>
