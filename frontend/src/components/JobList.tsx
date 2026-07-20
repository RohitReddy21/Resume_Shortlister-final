import React, { useEffect, useState } from "react"
import { listJobs, deleteJob } from "../api/jobsApi"

export default function JobList() {
  const [jobs, setJobs] = useState<any[]>([])

  useEffect(() => {
    load()
  }, [])

  async function load() {
    const data = await listJobs()
    setJobs(data || [])
  }

  async function handleDelete(id: string) {
    await deleteJob(id)
    load()
  }

  return (
    <div>
      <h2>Jobs</h2>
      <button onClick={load}>Refresh</button>
      <ul>
        {jobs.map((j) => (
          <li key={j.id}>
            <strong>{j.title}</strong> — {j.status}
            <button onClick={() => handleDelete(j.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
