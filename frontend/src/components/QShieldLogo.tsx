interface QShieldLogoProps {
  size?: number;
  /** SVG fill colour. Defaults to currentColor so it inherits from CSS. */
  color?: string;
  className?: string;
}

/**
 * QShield brand mark — angular shield / Q geometry.
 * viewBox 0 0 256 256, designed at 32×32 display size.
 */
export default function QShieldLogo({
  size = 32,
  color = '#192837',
  className = '',
}: QShieldLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 256 256"
      fill={color}
      xmlns="http://www.w3.org/2000/svg"
      aria-label="QShield logo"
      className={className}
    >
      <path d="M 64 128 L 64.5 128 L 32 95 L 0 64 L 0 0 L 64 0 L 128 64 L 128 64.5 L 161 32 L 192 0 L 256 0 L 256 64 L 192 128 L 128 128 L 128 192 L 96 223 L 63.5 256 L 0 256 L 0 192 Z M 256 192 L 224 223 L 191.5 256 L 128 256 L 128 192 L 192 128 L 256 128 Z" />
    </svg>
  );
}
