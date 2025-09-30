import { redirect } from 'next/navigation'

import { LogoutButton } from '@/components/auth/logout-button'
import { createClient } from '@/lib/supabase/server'
import { getProfile } from '@/lib/database/queries'

export default async function ProtectedPage() {
  const supabase = await createClient()

  const { data, error } = await supabase.auth.getClaims()
  if (error || !data?.claims) {
    redirect('/auth/login')
  }

  const userId = data.claims.sub

  try {
    // Check if user has a profile and if onboarding is completed
    const profile = await getProfile(userId)
    
    if (!profile || !profile.onboarding_completed) {
      redirect('/onboarding')
    }

    return (
      <div className="flex h-svh w-full items-center justify-center gap-2">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">
            Welcome back, {profile.full_name || data.claims.email}!
          </h1>
          <p className="text-muted-foreground">
            Your onboarding is complete. Ready to start your job search?
          </p>
          <LogoutButton />
        </div>
      </div>
    )
  } catch (error) {
    // If profile doesn't exist, redirect to onboarding
    console.error('Error fetching profile:', error)
    redirect('/onboarding')
  }
}
