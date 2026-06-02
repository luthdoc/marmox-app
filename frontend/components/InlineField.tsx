"use client";

import { useState, useRef } from "react";

interface InlineFieldProps {
  label: string;
  value: string;
  onSave: (value: string) => Promise<void>;
  validate: (value: string) => string | null;
  multiline?: boolean;
}

export function InlineField({
  label,
  value,
  onSave,
  validate,
  multiline = false,
}: InlineFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const [savedFeedback, setSavedFeedback] = useState(false);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function save() {
    const validationError = validate(draft);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    await onSave(draft);
    setEditing(false);
    setSavedFeedback(true);

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(() => setSavedFeedback(false), 2000);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !multiline) {
      e.preventDefault();
      save();
    }
    if (e.key === "Escape") {
      setDraft(value);
      setEditing(false);
      setError(null);
    }
  }

  const inputClasses =
    "w-full rounded-[8px] border border-[var(--color-hairline)] px-3 py-2 text-[17px] text-[var(--color-ink)] outline-none focus:border-[var(--color-action-blue)]";

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
        {label}
      </span>

      {editing ? (
        <>
          {multiline ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={save}
              onKeyDown={handleKeyDown}
              className={`${inputClasses} resize-y min-h-[80px]`}
              autoFocus
            />
          ) : (
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={save}
              onKeyDown={handleKeyDown}
              className={inputClasses}
              autoFocus
            />
          )}
          {error && (
            <span className="text-xs text-red-600">{error}</span>
          )}
        </>
      ) : (
        <button
          type="button"
          onClick={() => {
            setDraft(value);
            setEditing(true);
            setSavedFeedback(false);
          }}
          className="text-left text-[17px] text-[var(--color-ink)] hover:text-[var(--color-action-blue)] transition-colors"
        >
          {value || <span className="text-[var(--color-ink-muted)]">Clique para editar</span>}
        </button>
      )}

      {savedFeedback && !editing && (
        <span className="text-xs text-green-600">Salvo</span>
      )}
    </div>
  );
}
