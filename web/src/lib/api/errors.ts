export interface ApiErrorDetail {
  field?: string;
  message: string;
  [key: string]: unknown;
}

interface ApiErrorBody {
  code: string;
  message: string;
  details: ApiErrorDetail[];
  requestId: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetail[];
  readonly requestId: string;

  constructor(
    status: number,
    code: string,
    message: string,
    details: ApiErrorDetail[] = [],
    requestId = "",
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  static from(status: number, body: unknown): ApiError {
    if (isApiErrorBody(body)) {
      return new ApiError(
        status,
        body.code,
        body.message,
        body.details ?? [],
        body.requestId ?? "",
      );
    }
    return new ApiError(status, "internal_error", "请求失败。");
  }

  fieldError(field: string): string | undefined {
    return this.details.find((item) => item.field === field)?.message;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.code === "string" && typeof record.message === "string";
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
