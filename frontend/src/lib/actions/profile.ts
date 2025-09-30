'use server'

import { createClient } from '@/lib/supabase/server'
import { createProfile } from '@/lib/database/queries'

export async function createUserProfile(userId: string, email: string) {
  try {
    const profile = await createProfile({
      id: userId,
      email: email
    })
    return { success: true, profile }
  } catch (error) {
    console.error('Error creating user profile:', error)
    return { success: false, error: 'Failed to create profile' }
  }
}
