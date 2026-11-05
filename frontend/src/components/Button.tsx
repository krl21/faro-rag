import type { ButtonHTMLAttributes, ReactNode } from 'react';
import styles from './Button.module.css';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  icon?: ReactNode;
}

export function Button({
  variant = 'primary',
  icon,
  children,
  className,
  type = 'button',
  ...props
}: ButtonProps) {
  const classes = [styles.button, styles[variant], className].filter(Boolean).join(' ');
  return (
    <button type={type} className={classes} {...props}>
      {icon}
      {children}
    </button>
  );
}
