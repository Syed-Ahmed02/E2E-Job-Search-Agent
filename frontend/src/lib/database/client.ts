import { createClient } from '@/lib/supabase/client'

// Client-side database functions
// Use these in Client Components when you need real-time updates or client-side interactions

// Profile functions
export async function getProfileClient() {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', user.id)
    .single()

  if (error) {
    throw new Error(`Failed to fetch profile: ${error.message}`)
  }

  return data
}

export async function updateProfileClient(updates: {
  full_name?: string
  phone_number?: string
  linkedin_url?: string
  onboarding_completed?: boolean
}) {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  const { data, error } = await supabase
    .from('profiles')
    .update({ ...updates, updated_at: new Date().toISOString() })
    .eq('id', user.id)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to update profile: ${error.message}`)
  }

  return data
}

// Skills functions
export async function getAllSkillsClient() {
  const supabase = createClient()
  
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

export async function updateUserSkillsClient(skills: Array<{
  skill_id: string
  proficiency_level: string
}>) {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  // First, delete existing user skills
  await supabase
    .from('user_skills')
    .delete()
    .eq('user_id', user.id)

  // Then insert new skills
  if (skills.length > 0) {
    const skillsWithUserId = skills.map(skill => ({
      ...skill,
      user_id: user.id
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

// Resume functions
export async function getUserResumesClient() {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  const { data, error } = await supabase
    .from('resumes')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })

  if (error) {
    throw new Error(`Failed to fetch user resumes: ${error.message}`)
  }

  return data
}

export async function createResumeClient(resumeData: {
  file_url: string
  file_name: string
  parsed_content?: any
  is_master?: boolean
}) {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  const { data, error } = await supabase
    .from('resumes')
    .insert({
      ...resumeData,
      user_id: user.id
    })
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create resume: ${error.message}`)
  }

  return data
}

export async function setMasterResumeClient(resumeId: string) {
  const supabase = createClient()
  
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) {
    throw new Error('User not authenticated')
  }

  // First, unset all other master resumes for this user
  await supabase
    .from('resumes')
    .update({ is_master: false })
    .eq('user_id', user.id)

  // Then set the selected resume as master
  const { data, error } = await supabase
    .from('resumes')
    .update({ is_master: true })
    .eq('id', resumeId)
    .eq('user_id', user.id)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to set master resume: ${error.message}`)
  }

  return data
}

// File upload function
export async function uploadFile(file: File, bucket: string, path: string) {
  const supabase = createClient()
  
  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(path, file)

  if (error) {
    throw new Error(`Failed to upload file: ${error.message}`)
  }

  return data
}
