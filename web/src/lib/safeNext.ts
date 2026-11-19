export function safeNextPath(value: string | null | undefined): string {
  if (!value || value.includes("\r") || value.includes("\n")) {
    return "/";
  }
  if (
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.startsWith("/\\")
  ) {
    return "/";
  }
  if (value.toLowerCase().startsWith("/%2f")) {
    return "/";
  }
  return value;
}
