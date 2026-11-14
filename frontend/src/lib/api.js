import { useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_BASE || "";
const cache = new Map();

export function apiUrl(path, params = {}) {
  const q = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return `${BASE}/api/${path}${q ? `?${q}` : ""}`;
}

export async function api(path, params = {}, signal) {
  const url = apiUrl(path, params);
  if (cache.has(url)) return cache.get(url);
  const res = await fetch(url, { signal });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `The server returned an error (${res.status}).`);
  cache.set(url, body);
  return body;
}

export function useApi(path, params, enabled = true) {
  const key = enabled && path ? apiUrl(path, params) : null;
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(key) });

  useEffect(() => {
    if (!key) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    if (cache.has(key)) {
      setState({ data: cache.get(key), error: null, loading: false });
      return;
    }
    const ctrl = new AbortController();
    setState((s) => ({ data: s.data, error: null, loading: true }));
    api(path, params, ctrl.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((e) => {
        if (e.name !== "AbortError") setState({ data: null, error: e.message, loading: false });
      });
    return () => ctrl.abort();
  }, [key]);

  return state;
}
