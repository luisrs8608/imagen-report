import { useEffect, useId, useRef, useState } from 'react';
import {
  Check,
  Clipboard,
  Expand,
  Loader2,
  Minimize2,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

interface ReportDraftEditorProps {
  value: string;
  generatedDraft: string;
  approved: boolean;
  canGenerate: boolean;
  isGenerating: boolean;
  onChange: (value: string) => void;
  onGenerate: () => void;
}

type CopyState = 'idle' | 'copied' | 'error';

export function ReportDraftEditor({
  value,
  generatedDraft,
  approved,
  canGenerate,
  isGenerating,
  onChange,
  onGenerate,
}: ReportDraftEditorProps) {
  const textareaId = useId();
  const helpId = useId();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [copyState, setCopyState] = useState<CopyState>('idle');

  const trimmedValue = value.trim();
  const wordCount = trimmedValue ? trimmedValue.split(/\s+/u).length : 0;
  const characterCount = value.length;
  const lineCount = value ? value.split(/\r\n|\r|\n/u).length : 0;
  const hasGeneratedVersion = Boolean(generatedDraft.trim());
  const differsFromGenerated = hasGeneratedVersion && value !== generatedDraft;

  const reviewState = !trimmedValue
    ? { label: 'Sin borrador', className: 'empty' }
    : approved
      ? { label: 'Revisado y aprobado', className: 'approved' }
      : differsFromGenerated
        ? { label: 'Editado · falta aprobar', className: 'edited' }
        : { label: 'Pendiente de revisión', className: 'pending' };

  useEffect(() => {
    if (!expanded) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.requestAnimationFrame(() => textareaRef.current?.focus());

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setExpanded(false);
    }

    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [expanded]);

  useEffect(() => {
    if (copyState === 'idle') return undefined;
    const timer = window.setTimeout(() => setCopyState('idle'), 1800);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(value);
      setCopyState('copied');
    } catch {
      setCopyState('error');
    }
  }

  function restoreGeneratedDraft() {
    if (!hasGeneratedVersion || !differsFromGenerated) return;
    const confirmed = window.confirm(
      'Se reemplazarán las correcciones actuales por el último borrador generado por IA. ¿Continuar?',
    );
    if (confirmed) onChange(generatedDraft);
  }

  return (
    <div className={`draft-editor${expanded ? ' is-expanded' : ''}`}>
      <div className="draft-editor-toolbar">
        <div className="draft-editor-status">
          <span className={`draft-status-dot ${reviewState.className}`} aria-hidden="true" />
          <div>
            <strong>{reviewState.label}</strong>
            <small>Editor de texto del documento final</small>
          </div>
        </div>

        <div className="draft-editor-tools" aria-label="Herramientas del editor">
          <button
            type="button"
            className="draft-tool-button"
            onClick={copyDraft}
            disabled={!value}
            title="Copiar informe"
          >
            {copyState === 'copied' ? <Check size={15} /> : <Clipboard size={15} />}
            {copyState === 'copied' ? 'Copiado' : copyState === 'error' ? 'No se pudo copiar' : 'Copiar'}
          </button>
          <button
            type="button"
            className="draft-tool-button"
            onClick={restoreGeneratedDraft}
            disabled={!differsFromGenerated}
            title="Restaurar el último texto generado por IA"
          >
            <RotateCcw size={15} /> Restaurar IA
          </button>
          <button
            type="button"
            className="draft-tool-button expand-tool"
            onClick={() => setExpanded((current) => !current)}
            aria-pressed={expanded}
            title={expanded ? 'Cerrar pantalla completa' : 'Editar en pantalla completa'}
          >
            {expanded ? <Minimize2 size={15} /> : <Expand size={15} />}
            {expanded ? 'Cerrar' : 'Ampliar'}
          </button>
        </div>
      </div>

      <label className="draft-editor-label" htmlFor={textareaId}>
        Texto del informe
      </label>
      <textarea
        ref={textareaRef}
        id={textareaId}
        className="draft-editor-textarea"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Genere el borrador y edítelo aquí..."
        aria-describedby={helpId}
        lang="es"
        spellCheck
        autoCapitalize="sentences"
        required
      />

      <div className="draft-editor-footer" id={helpId}>
        <span>{wordCount} palabras · {characterCount} caracteres · {lineCount} líneas</span>
        <span>{approved ? 'La aprobación está vigente.' : 'Cualquier edición requiere una nueva aprobación.'}</span>
      </div>

      <div className="draft-editor-actions">
        <button
          type="button"
          className="ai-button"
          onClick={onGenerate}
          disabled={!canGenerate || isGenerating}
        >
          {isGenerating ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
          {isGenerating ? 'Generando…' : hasGeneratedVersion ? 'Regenerar borrador' : 'Generar borrador'}
        </button>
      </div>
    </div>
  );
}
