import { redirect } from 'next/navigation'

import { LogoutButton } from '@/components/auth/logout-button'
import { createClient } from '@/lib/supabase/server'
import { getProfile } from '@/lib/database/queries'
import { ChatInputDemo } from '@/components/ChatInput'
import { DataTable } from './data-table'
import { columns } from './columns'
import { sampleJobListings } from './sample-data'

export default async function ProtectedPage() {
  const supabase = await createClient()

  const { data, error } = await supabase.auth.getClaims()
  if (error || !data?.claims) {
    redirect('/auth/login')
  }

  const userId = data.claims.sub

  const profile = await getProfile(userId)
  console.log(profile)

  return (
    <div className="container mx-auto py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Hey {profile.full_name}</h1>
        <h2 className="text-xl text-muted-foreground mb-6">
          Here are your job listings with match ratings
        </h2>
      </div>
      
      <DataTable columns={columns} data={sampleJobListings} />
      
      
    </div>
  );
}
