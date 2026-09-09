import React from 'react';

/**
 * EnroloLogo — Official branding component for Enrolo.
 *
 * @param {string} variant - 'full' (emblem + text) | 'icon' (emblem only)
 * @param {number} height - pixel height of the logo (default 34)
 * @param {object} style - optional additional styles
 * @param {function} onClick - optional click handler
 */
export default function EnroloLogo({
  variant = 'full',
  height = 34,
  style = {},
  onClick = undefined,
  className = '',
}) {
  const isIcon = variant === 'icon';
  const logoSrc = isIcon ? '/enrolo-icon.png' : '/enrolo-logo.png';

  return (
    <div
      className={`enrolo-logo-wrap ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        cursor: onClick ? 'pointer' : 'default',
        userSelect: 'none',
        ...style,
      }}
      onClick={onClick}
    >
      <img
        src={logoSrc}
        alt="Enrolo"
        style={{
          height: `${height}px`,
          width: 'auto',
          objectFit: 'contain',
          display: 'block',
        }}
      />
    </div>
  );
}
