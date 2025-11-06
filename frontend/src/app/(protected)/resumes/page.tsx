import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getAllResumesWithProfiles } from '@/lib/database/queries'
import { ResumeCard } from '@/components/ResumeCard'
import { FileText, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default async function ResumesPage() {
  const supabase = await createClient()

  const { data, error } = await supabase.auth.getClaims()
  if (error || !data?.claims) {
    redirect('/auth/login')
  }

  let resumes = []
  let errorMessage = ''

  try {
    resumes = await getAllResumesWithProfiles()
  } catch (err: any) {
    console.error('Error fetching resumes:', err)
    errorMessage = err.message || 'Failed to load resumes'
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Resumes</h1>
          <p className="text-muted-foreground mt-2">
            View and manage all uploaded resumes
          </p>
        </div>
        <Button >
          <Link href="/onboarding">
            <Plus className="h-4 w-4 mr-2" />
            Upload Resume
          </Link>
        </Button>
      </div>

      {/* Error state */}
      {errorMessage && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-md mb-6">
          <p className="font-medium">Error loading resumes</p>
          <p className="text-sm mt-1">{errorMessage}</p>
        </div>
      )}

      {/* Empty state */}
      {!errorMessage && resumes.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto w-24 h-24 bg-muted rounded-full flex items-center justify-center mb-4">
            <FileText className="h-12 w-12 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No resumes found</h3>
          <p className="text-muted-foreground mb-6">
            Upload your first resume to get started with job matching
          </p>
          <Button>
            <Link href="/onboarding">
              <Plus className="h-4 w-4 mr-2" />
              Upload Resume
            </Link>
          </Button>
        </div>
      )}

      {/* Resumes grid */}
      {!errorMessage && resumes.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes.map((resume) => (
            <ResumeCard key={resume.id} resume={resume} />
          ))}
        </div>
      )}

      {/* Stats - moved to bottom */}
      {!errorMessage && resumes.length > 0 && (
        <div className="mt-12 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Total resumes: {resumes.length}</span>
            <span>
              Master resume: {resumes.find(r => r.is_master)?.file_name || 'None set'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
