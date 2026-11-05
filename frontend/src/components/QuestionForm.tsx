import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { config } from '../config';
import { Button } from './Button';
import forms from './forms.module.css';
import { SendIcon } from './icons/icons';
import styles from './QuestionForm.module.css';

/** The box grows with the text up to this many lines; then it scrolls inside. */
const MAX_LINES = 3;

/** Fits the textarea height to its text, up to `MAX_LINES` lines. */
function fitHeight(textarea: HTMLTextAreaElement) {
  const style = window.getComputedStyle(textarea);
  const lineHeight = parseFloat(style.lineHeight);
  if (Number.isNaN(lineHeight)) return; // No layout (for example in tests)
  const border = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
  const padding = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
  const maxHeight = lineHeight * MAX_LINES + padding + border;

  textarea.style.height = 'auto'; // Measures the text, not the previous height
  // `scrollHeight` includes the padding but not the border (box-sizing: border-box).
  const needed = textarea.scrollHeight + border;
  textarea.style.height = `${Math.min(needed, maxHeight)}px`;
  textarea.style.overflowY = needed > maxHeight ? 'auto' : 'hidden';
}

interface QuestionFormProps {
  disabled: boolean;
  placeholder: string;
  onAsk: (question: string) => void;
}

/** Question box: Enter sends, Shift+Enter adds a line. */
export function QuestionForm({ disabled, placeholder, onAsk }: QuestionFormProps) {
  const [question, setQuestion] = useState('');
  const textarea = useRef<HTMLTextAreaElement>(null);
  const trimmed = question.trim();
  const canSend = !disabled && trimmed.length >= config.questionMinLength;

  useLayoutEffect(() => {
    if (textarea.current) fitHeight(textarea.current);
  }, [question]);

  const send = () => {
    if (!canSend) return;
    onAsk(trimmed);
    setQuestion('');
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    send();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send();
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.input}>
        <textarea
          ref={textarea}
          aria-label="Pregunta"
          className={`${forms.control} ${styles.question}`}
          rows={1}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={config.questionMaxLength}
          disabled={disabled}
        />
      </div>
      <Button type="submit" icon={<SendIcon size={18} />} disabled={!canSend}>
        Enviar
      </Button>
    </form>
  );
}
