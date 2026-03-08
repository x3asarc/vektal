import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'icon';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Global Button component utilizing the "Forensic OS" design identity.
 * Uses the .btn-primary and .btn-ghost classes from forensic-theme.css.
 */
export const Button: React.FC<ButtonProps> = ({ 
  variant = 'primary', 
  size = 'md', 
  className = '', 
  children, 
  ...props 
}) => {
  const baseStyles = "inline-flex items-center justify-center transition-all duration-200 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed";
  
  const variantClasses = {
    primary: "btn-primary",
    secondary: "btn-ghost", // Mapping secondary to ghost as per forensic system
    ghost: "btn-ghost",
    icon: "p-2 bg-transparent text-[var(--text-body)] hover:text-[var(--text-heading)] hover:bg-white/5 border-none"
  };

  const sizes = {
    sm: "h-8 px-4 text-[9px]",
    md: "h-10 px-6 text-[10px]",
    lg: "h-12 px-8 text-xs"
  };

  const variantClass = variantClasses[variant];
  const sizeClass = variant === 'icon' ? '' : sizes[size];

  return (
    <button 
      className={`${baseStyles} ${variantClass} ${sizeClass} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
