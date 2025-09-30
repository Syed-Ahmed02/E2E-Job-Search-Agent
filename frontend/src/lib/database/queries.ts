import { createClient } from '@/lib/supabase/server'

// Profile-related queries
export async function getProfile(userId: string) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', userId)
    .single()

  if (error) {
    throw new Error(`Failed to fetch profile: ${error.message}`)
  }

  return data
}

export async function createProfile(profileData: {
  id: string
  email: string
  full_name?: string
  phone_number?: string
  linkedin_url?: string
}) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('profiles')
    .insert(profileData)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create profile: ${error.message}`)
  }

  return data
}

export async function updateProfile(userId: string, updates: {
  full_name?: string
  phone_number?: string
  linkedin_url?: string
  onboarding_completed?: boolean
}) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('profiles')
    .update({ ...updates, updated_at: new Date().toISOString() })
    .eq('id', userId)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to update profile: ${error.message}`)
  }

  return data
}

// Skills-related queries
export async function getAllSkills() {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('skills')
    .select('*')
    .order('category', { ascending: true })
    .order('name', { ascending: true })

  if (error) {
    throw new Error(`Failed to fetch skills: ${error.message}`)
  }

  return data
}

export async function getUserSkills(userId: string) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('user_skills')
    .select(`
      *,
      skills (
        id,
        name,
        category
      )
    `)
    .eq('user_id', userId)

  if (error) {
    throw new Error(`Failed to fetch user skills: ${error.message}`)
  }

  return data
}

export async function updateUserSkills(userId: string, skills: Array<{
  skill_id: string
  proficiency_level: string
}>) {
  const supabase = await createClient()
  
  // First, delete existing user skills
  await supabase
    .from('user_skills')
    .delete()
    .eq('user_id', userId)

  // Then insert new skills
  if (skills.length > 0) {
    const skillsWithUserId = skills.map(skill => ({
      ...skill,
      user_id: userId
    }))

    const { data, error } = await supabase
      .from('user_skills')
      .insert(skillsWithUserId)
      .select()

    if (error) {
      throw new Error(`Failed to update user skills: ${error.message}`)
    }

    return data
  }

  return []
}

// Resume-related queries
export async function getUserResumes(userId: string) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('resumes')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })

  if (error) {
    throw new Error(`Failed to fetch user resumes: ${error.message}`)
  }

  return data
}

export async function createResume(resumeData: {
  user_id: string
  file_url: string
  file_name: string
  parsed_content?: any
  is_master?: boolean
}) {
  const supabase = await createClient()
  
  const { data, error } = await supabase
    .from('resumes')
    .insert(resumeData)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create resume: ${error.message}`)
  }

  return data
}
