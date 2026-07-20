import React, { useState } from "react"
import { createJob } from "../api/jobsApi"

export default function JobForm({ onCreated }: { onCreated?: () => void }) {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")

  async function handleSubmit(e: any) {
    e.preventDefault()
    await createJob({ title, description })
    setTitle("")
    setDescription("")
    if (onCreated) onCreated()
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Title</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div>
        <label>Description</label>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <button type="submit">Create</button>
    </form>
  )
}
