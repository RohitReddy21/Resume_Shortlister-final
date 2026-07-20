const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1"

export async function listJobs(status?: string) {
  const url = new URL(`${API_BASE}/jobs`)
  if (status) url.searchParams.set("status", status)
  const res = await fetch(url.toString())
  return res.json()
}

export async function createJob(payload: any) {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return res.json()
}

export async function getJob(id: string) {
  const res = await fetch(`${API_BASE}/jobs/${id}`)
  return res.json()
}

export async function updateJob(id: string, payload: any) {
  const res = await fetch(`${API_BASE}/jobs/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return res.json()
}

export async function deleteJob(id: string) {
  return fetch(`${API_BASE}/jobs/${id}`, { method: "DELETE" })
}
