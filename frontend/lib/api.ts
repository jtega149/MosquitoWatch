export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/backend";

export type ApiZip = {
  zip_code: string;
  borough: string;
  areas: string;
};

export type ApiForecast = {
  zip_code: string;
  forecast_week: number;
  forecast_year: number;
  risk_score: number;
  risk_level: string;
};

export type ApiForecastDay = {
  date: string;
  risk_score: number;
  risk_level: string;
};

export type ApiIndicators = {
  positive_prev_week: number;
  positive_prev_2_weeks: number;
  positive_prev_4_weeks: number;
  temperature: number;
  rainfall: number;
  seasonality: string | null;
};

export type ApiPrediction = {
  zip_code: string;
  borough: string;
  areas: string;
  forecast_week: number;
  forecast_year: number;
  risk_score: number;
  risk_level: string;
  indicators: ApiIndicators;
  next_7_days: ApiForecastDay[];
  explanation: string;
};

export type ApiTrendPoint = {
  year: number;
  week: number;
  positive_detections: number;
};

export type ApiTrends = {
  zip_code: string;
  history: ApiTrendPoint[];
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) detail = body.detail;
  } catch {
    /* keep default */
  }
  return new ApiError(detail, response.status);
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export function fetchHealth() {
  return apiGet<{ status: string }>("/health");
}

export function fetchZips() {
  return apiGet<ApiZip[]>("/zips");
}

export function fetchForecasts() {
  return apiGet<ApiForecast[]>("/forecasts");
}

export function fetchPrediction(zipCode: string) {
  return apiPost<ApiPrediction>("/predict", { zip_code: zipCode });
}

export function fetchTrends(zipCode: string) {
  return apiGet<ApiTrends>(`/trends/${zipCode}`);
}

export type ApiChatResponse = {
  reply: string;
  cached: boolean;
  similarity: number | null;
};

export function fetchChat(message: string) {
  return apiPost<ApiChatResponse>("/chat", { message });
}
