/**
 * Tiny HTTP wrapper: fetchJson<T>, typed ApiError, default headers.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_HEADERS: Record<string, string> = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

export async function fetchJson<T>(
  url: string,
  options: RequestInit & { parseJson?: boolean } = {}
): Promise<T> {
  const { parseJson = true, headers: optHeaders, ...rest } = options;
  const headers = { ...DEFAULT_HEADERS, ...optHeaders } as Record<string, string>;

  const res = await fetch(url, { ...rest, headers });

  let body: unknown = null;
  const ct = res.headers.get("Content-Type") ?? "";
  if (ct.includes("application/json")) {
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
  } else {
    body = await res.text();
  }

  if (!res.ok) {
    let message = `Request failed: ${res.status} ${res.statusText}`;
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") message = detail;
      else if (
        typeof detail === "object" &&
        detail !== null &&
        "message" in detail &&
        typeof (detail as { message: unknown }).message === "string"
      )
        message = (detail as { message: string }).message;
      else message = String(detail);
    }
    throw new ApiError(message, res.status, body);
  }

  if (!parseJson) {
    return body as T;
  }
  return body as T;
}
