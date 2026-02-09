import { useEffect, useState } from "react"

const API = import.meta.env.VITE_BACKEND_URL

export function useJobs(interval = 2000) {
  const [jobs, setJobs] = useState([])

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch(`${API}/api/jobs`)
        setJobs(await res.json())
      } catch (e) {
        console.error("Failed to fetch jobs", e)
      }
    }

    fetchJobs()
    const id = setInterval(fetchJobs, interval)
    return () => clearInterval(id)
  }, [])

  const getActiveJobs = (type = null) =>
    jobs.filter(
      j =>
        ["queued", "running"].includes(j.status) &&
        (type ? j.type === type : true)
    )

  const isJobRunning = (type = null) =>
    getActiveJobs(type).length > 0

  return {
    jobs,
    getActiveJobs,
    isJobRunning
  }
}
