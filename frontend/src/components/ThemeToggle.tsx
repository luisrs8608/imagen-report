import { Moon, Sun } from 'lucide-react';

export type ColorTheme = 'light' | 'dark';

interface ThemeToggleProps {
  theme: ColorTheme;
  onToggle: () => void;
  className?: string;
}

export function ThemeToggle({ theme, onToggle, className = '' }: ThemeToggleProps) {
  const darkModeActive = theme === 'dark';
  const label = darkModeActive ? 'Activar modo claro' : 'Activar modo oscuro';

  return (
    <button
      type="button"
      className={`icon-button theme-toggle ${className}`.trim()}
      onClick={onToggle}
      aria-label={label}
      title={label}
    >
      {darkModeActive
        ? <Sun size={18} aria-hidden="true" />
        : <Moon size={18} aria-hidden="true" />}
    </button>
  );
}
