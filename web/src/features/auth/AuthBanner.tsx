export interface AuthBannerProps {
  tone: "info" | "danger";
  children: string;
}

export function AuthBanner({ tone, children }: AuthBannerProps) {
  return (
    <p role="status" data-tone={tone} style={{ color: `var(--color-${tone})` }}>
      {children}
    </p>
  );
}
