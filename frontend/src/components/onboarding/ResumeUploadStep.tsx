'use client'

import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/dropzone'
import { useSupabaseUpload } from '@/hooks/use-supabase-upload'
import { createResumeClient } from '@/lib/database/client'
import { createClient } from '@/lib/supabase/client'

interface ResumeUploadStepProps {
  onNext: () => void
  onBack: () => void
}

export function ResumeUploadStep({ onNext, onBack }: ResumeUploadStepProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [uploadSuccess, setUploadSuccess] = useState(false)

  const supabase = createClient()

  const uploadHook = useSupabaseUpload({
    bucketName: 'resumes',
    path: '', // We'll set the path dynamically with user ID
    allowedMimeTypes: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    maxFileSize: 5 * 1024 * 1024, // 5MB
    maxFiles: 1,
    upsert: true
  })

  const handleUpload = useCallback(async () => {
    if (uploadHook.files.length === 0) {
      setError('Please select a resume file to upload.')
      return
    }

    setLoading(true)
    setError('')

    try {
      // Check if user is authenticated
      const { data: { user }, error: authError } = await supabase.auth.getUser()
      if (authError || !user) {
        setError('You must be logged in to upload a resume.')
        return
      }

      // Upload files to Supabase storage with user-specific path
      const file = uploadHook.files[0]
      const userId = user.id
      const fileName = `${userId}/${file.name}`
      
      // Upload the file directly with user-specific path
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('resumes')
        .upload(fileName, file, {
          upsert: true
        })

      if (uploadError) {
        setError(`Failed to upload resume: ${uploadError.message}`)
        return
      }

      // Get the public URL for the uploaded file
      const { data: { publicUrl } } = supabase.storage
        .from('resumes')
        .getPublicUrl(fileName)

      // Create resume record in database
      await createResumeClient({
        file_url: publicUrl,
        file_name: file.name,
        is_master: true // First resume is automatically master
      })

      setUploadSuccess(true)
    } catch (err: any) {
      console.error('Error uploading resume:', err)
      setError(`Failed to upload resume: ${err.message || 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }, [uploadHook, supabase.storage, supabase.auth])

  const handleNext = () => {
    if (uploadSuccess) {
      onNext()
    } else {
      setError('Please upload a resume before continuing.')
    }
  }

  const handleSkip = () => {
    onNext()
  }

  return (
    <Card className="w-full max-w-2xl mx-auto p-6">
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Upload your resume</h2>
          <p className="text-muted-foreground mt-2">
            Upload your resume to get personalized job recommendations
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-center">
            {error}
          </div>
        )}

        {/* Success Message */}
        {uploadSuccess && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-center">
            Resume uploaded successfully!
          </div>
        )}

        {/* Dropzone */}
        <Dropzone {...uploadHook}>
          <DropzoneEmptyState />
          <DropzoneContent />
        </Dropzone>

        {/* File Requirements */}
        <div className="text-sm text-muted-foreground space-y-1">
          <p><strong>Supported formats:</strong> PDF, DOC, DOCX</p>
          <p><strong>Maximum file size:</strong> 5MB</p>
          <p><strong>Note:</strong> Your resume will be used to match you with relevant job opportunities</p>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleSkip}>
              Skip for now
            </Button>
            {!uploadSuccess ? (
              <Button 
                onClick={handleUpload} 
                disabled={uploadHook.files.length === 0 || loading}
              >
                {loading ? 'Uploading...' : 'Upload Resume'}
              </Button>
            ) : (
              <Button onClick={handleNext}>
                Continue
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}
