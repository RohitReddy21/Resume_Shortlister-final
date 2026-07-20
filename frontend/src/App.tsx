import React from "react"
import JobList from "./components/JobList"
import JobForm from "./components/JobForm"

function App() {
  return (
    <div style={{ padding: 20 }}>
      <h1>Job Management</h1>
      <JobForm />
      <JobList />
    </div>
  )
}

export default App
