import { redirect } from 'next/navigation'

import { createClient } from '@/lib/supabase/server'
import { getProfile, getUserJobs } from '@/lib/database/queries'
import { DataTable } from './data-table'
import { columns } from './columns'
import { JobListing } from './types'

export default async function ProtectedPage() {
  const supabase = await createClient()

  const { data, error } = await supabase.auth.getClaims()
  if (error || !data?.claims) {
    redirect('/auth/login')
  }

  const userId = data.claims.sub

  const profile = await getProfile(userId)
  const jobs = await getUserJobs(userId)

  // Map database jobs to JobListing format
  const jobListings: JobListing[] = jobs.map((job) => ({
    title: job.job_title,
    company: job.company,
    snippit: job.location || '', // Use location as snippet since it's not in DB
    rating: job.match_rating ? job.match_rating / 5 : 0, // Convert 0-5 scale to 0-1 scale
    link: job.link,
  }))

  return (
    <div className="container mx-auto py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Hey {profile.full_name}</h1>
        <h2 className="text-xl text-muted-foreground mb-6">
          Here are your job listings with match ratings
        </h2>
      </div>
      
      <DataTable columns={columns} data={jobListings} />
      
      
    </div>
  );
}
