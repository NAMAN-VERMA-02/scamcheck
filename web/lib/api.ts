export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, cache: "no-store", headers: { "Content-Type": "application/json" } });
  } catch {
    throw new ApiError("Cannot reach the analysis API. Is the backend running on port 8000?", 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* non-JSON error body: keep the generic message */
    }
    if (res.status >= 500) detail = "Cannot reach the analysis API. Is the backend running on port 8000?";
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const pct = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined ? "n/a" : `${(x * 100).toFixed(digits)}%`;
