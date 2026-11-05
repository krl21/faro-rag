import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionForm } from '../../components/QuestionForm';

function setup() {
  const onAsk = vi.fn();
  render(<QuestionForm disabled={false} placeholder="Escribe tu pregunta…" onAsk={onAsk} />);
  return { onAsk, box: screen.getByRole('textbox', { name: 'Pregunta' }) };
}

describe('QuestionForm', () => {
  it('sends with Enter and clears the box', async () => {
    const { onAsk, box } = setup();
    await userEvent.type(box, '¿Qué cubre?{Enter}');
    expect(onAsk).toHaveBeenCalledWith('¿Qué cubre?');
    expect(box).toHaveValue('');
  });

  it('adds a line with Shift+Enter instead of sending', async () => {
    const { onAsk, box } = setup();
    await userEvent.type(box, 'Primera línea{Shift>}{Enter}{/Shift}segunda');
    expect(onAsk).not.toHaveBeenCalled();
    expect(box).toHaveValue('Primera línea\nsegunda');
  });
});
