const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetcher(endpoint: string, options: RequestInit = {}) {
  const url = `${API_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`Error fetching ${url}:`, error);
    return null;
  }
}
