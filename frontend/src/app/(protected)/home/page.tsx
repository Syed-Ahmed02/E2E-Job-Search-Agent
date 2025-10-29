import { redirect } from 'next/navigation'

import { LogoutButton } from '@/components/auth/logout-button'
import { createClient } from '@/lib/supabase/server'
import { getProfile } from '@/lib/database/queries'
import { ChatInputDemo } from '@/components/ChatInput'
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
      <div className="flex w-full h-screen justify-center items-center ">
    <div className="p-4">
      <div className='max-w-xl text-center gap-4 flex flex-col mb-16'>
        <h1 className='text-3xl font-bold '>Hey {profile.full_name}</h1>
        <h2 className='text-2xl font-medium'>I'm your Job Agent here to help you, ask me a question related to your job serach</h2>
      </div>
      <ChatInputDemo />
    </div>
    </div>
  );
  
}
